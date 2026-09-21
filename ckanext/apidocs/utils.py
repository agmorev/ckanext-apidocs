"""Discovery of CKAN API actions and parsing of their docstrings.

The module is deliberately free of side effects: unlike the previous
implementation it never mutates the discovered action functions, and all
failures coming from third party plugins are logged instead of being
silently ignored.
"""

from __future__ import annotations

import importlib
import inspect
import logging
import re
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from typing import Any

from ckan import authz
from ckan import plugins as p

from ckanext.apidocs import config


log = logging.getLogger(__name__)

CORE_ORIGIN = "core"
CORE_ACTION_MODULES = ("get", "create", "update", "patch", "delete")
APIDOCS_METHOD_ATTR = "apidocs_method"
FALLBACK_METHOD = "POST"

MODULE_METHODS = {
    "get": "GET",
    "create": "POST",
    "update": "PUT",
    "patch": "PATCH",
    "delete": "DELETE",
}

GET_NAME_PREFIXES = ("get_", "list_")
GET_NAME_SUFFIXES = ("_list", "_show", "_search", "_autocomplete", "_dump")

_PARAM_RE = re.compile(r"^:param:?\s+(?P<head>[^:]+):\s*(?P<desc>.*)$")
_TYPE_RE = re.compile(r"^:type:?\s+(?P<name>[^:]+):\s*(?P<type>.*)$")
_RETURN_RE = re.compile(r"^:returns?:?\s*(?P<desc>.*)$")
_RTYPE_RE = re.compile(r"^:rtype:?\s*(?P<type>.*)$")
_RAISES_RE = re.compile(r"^:raises?:?\s*(?P<exc>[^:]*):\s*(?P<desc>.*)$")
_NOTE_RE = re.compile(r"^(?:\.\.\s*note::?|Note:)\s*(?P<desc>.*)$")
_REQUIRED_RE = re.compile(r"(?<!not )(?<!non-)\b(required|mandatory)\b", re.IGNORECASE)

# Directives that can start a line and therefore end the summary paragraph.
_DIRECTIVES = (_PARAM_RE, _TYPE_RE, _RETURN_RE, _RTYPE_RE, _RAISES_RE, _NOTE_RE)


@dataclass
class ParamInfo:
    """A single documented action argument."""

    name: str
    type: str = ""
    description: str = ""
    required: bool = False

    def as_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "type": self.type,
            "description": self.description,
            "required": self.required,
        }


@dataclass
class ParsedDocstring:
    """Structured representation of a CKAN action docstring."""

    summary: str = ""
    description: str = ""
    params: dict[str, ParamInfo] = field(default_factory=dict)
    returns: str = ""
    returns_type: str = ""

    def params_dict(self) -> dict[str, dict[str, Any]]:
        """Parameters as plain dictionaries, ready for the schema builder."""
        return {name: info.as_dict() for name, info in self.params.items()}


@dataclass
class ActionInfo:
    """A discovered API action together with its inferred HTTP method."""

    name: str
    func: Callable[..., Any]
    method: str
    origin: str
    module: str = ""
    chained: bool = False
    side_effect_free: bool = False

    def badges(self) -> list[str]:
        badges = [self.origin] if self.origin else []
        if self.chained:
            badges.append("chained")
        return badges


def _is_summary_line(line: str) -> bool:
    """Whether the line still belongs to the summary paragraph.

    The summary ends at the first blank line, at an indented block and at
    every ReST directive. Its own lines are flush left because
    ``inspect.cleandoc`` removed the docstring indentation.
    """
    stripped = line.strip()
    if not stripped or line[0].isspace():
        return False

    return not any(pattern.match(stripped) for pattern in _DIRECTIVES)


@dataclass
class _DocstringState:
    """Mutable state of the docstring parser."""

    parsed: ParsedDocstring = field(default_factory=ParsedDocstring)
    description_lines: list[str] = field(default_factory=list)
    returns_parts: list[str] = field(default_factory=list)
    current: str | None = None


def parse_docstring(doc: str | None) -> ParsedDocstring:
    """Parse a ReST style CKAN docstring.

    The summary is the complete first paragraph, with its wrapped lines
    joined back into a single sentence. Understands the ``:param:``,
    ``:type:``, ``:returns:``, ``:rtype:``, ``:raises:`` and ``.. note::``
    directives, their indented continuations and plain text paragraphs.
    Malformed lines are ignored instead of producing garbage descriptions.
    """
    if not doc:
        return ParsedDocstring()

    lines = inspect.cleandoc(doc).splitlines()
    state = _DocstringState()

    _parse_summary(state, lines)

    for line in lines:
        _consume_line(state, line)

    return _finish(state)


def _parse_summary(state: _DocstringState, lines: list[str]) -> None:
    """Take the first paragraph as the summary, consuming its lines.

    The summary is wrapped in the docstring source, so its lines are
    joined back into a single sentence instead of leaking the wrapped part
    into the description.
    """
    summary_lines: list[str] = []

    while lines and _is_summary_line(lines[0]):
        summary_lines.append(lines.pop(0).strip())

    state.parsed.summary = " ".join(summary_lines).strip()


def _consume_line(state: _DocstringState, line: str) -> None:
    """Feed a single docstring line to the parser."""
    stripped = line.strip()

    if not stripped:
        _end_block(state)
        return

    indented = line[0].isspace()

    if not indented and _apply_directive(state, stripped):
        return

    _append_continuation(state, stripped, indented)


def _end_block(state: _DocstringState) -> None:
    """End the current block on a blank line.

    Inside the description the blank line is kept as a paragraph
    separator.
    """
    if state.current == "description":
        state.description_lines.append("")

    state.current = None


def _apply_directive(state: _DocstringState, line: str) -> bool:
    """Apply a ReST directive, reporting whether the line was one."""
    if match := _PARAM_RE.match(line):
        _set_param(state, match)
        return True

    if match := _TYPE_RE.match(line):
        _set_param_type(state, match)
        return True

    if match := _RETURN_RE.match(line):
        _set_returns(state, match)
        return True

    if match := _RTYPE_RE.match(line):
        _set_returns_type(state, match)
        return True

    if match := _RAISES_RE.match(line):
        _add_raises(state, match)
        return True

    if match := _NOTE_RE.match(line):
        _add_note(state, match)
        return True

    return False


def _set_param(state: _DocstringState, match: re.Match[str]) -> None:
    """Register a ``:param`` directive, merging repeated parameters."""
    info = _param_from_match(match)
    existing = state.parsed.params.get(info.name)

    if existing and existing.description:
        info.description = (
            f"{existing.description} {info.description}".strip()
        )

    if existing and not info.type:
        info.type = existing.type

    state.parsed.params[info.name] = info
    state.current = f"param:{info.name}"


def _set_param_type(state: _DocstringState, match: re.Match[str]) -> None:
    """Register a ``:type`` directive."""
    name = match.group("name").strip()
    info = state.parsed.params.setdefault(name, ParamInfo(name=name))
    info.type = match.group("type").strip()
    state.current = None


def _set_returns(state: _DocstringState, match: re.Match[str]) -> None:
    """Register a ``:returns`` directive."""
    value = match.group("desc").strip()

    if value:
        state.returns_parts.append(value)

    state.current = "returns"


def _set_returns_type(state: _DocstringState, match: re.Match[str]) -> None:
    """Register a ``:rtype`` directive."""
    value = match.group("type").strip()

    if value:
        state.parsed.returns_type = value

    state.current = "returns"


def _add_raises(state: _DocstringState, match: re.Match[str]) -> None:
    """Turn a ``:raises`` directive into a description bullet."""
    exception = match.group("exc").strip()
    value = match.group("desc").strip()
    detail = f"**Raises** {exception}".strip()

    if value:
        detail = f"{detail} - {value}"

    state.description_lines.append(detail)
    state.current = "description"


def _add_note(state: _DocstringState, match: re.Match[str]) -> None:
    """Turn a ``.. note::`` directive into a description paragraph."""
    note = match.group("desc")
    state.description_lines.append(f"**Note** {note}".rstrip())
    state.current = "description"


def _append_continuation(
    state: _DocstringState, line: str, indented: bool
) -> None:
    """Continue the block opened by one of the previous lines."""
    if state.current == "description":
        state.description_lines.append(line)
        return

    if state.current == "returns":
        state.returns_parts.append(line)
        return

    if state.current and state.current.startswith("param:"):
        _extend_param(state, state.current, line)
        return

    state.description_lines.append(line)

    if not indented:
        # A plain paragraph after the summary or after the directives.
        state.current = "description"


def _extend_param(state: _DocstringState, current: str, line: str) -> None:
    """Append an indented continuation to a parameter description."""
    name = current.split(":", 1)[1]
    info = state.parsed.params.setdefault(name, ParamInfo(name=name))
    info.description = f"{info.description} {line}".strip()


def _finish(state: _DocstringState) -> ParsedDocstring:
    """Assemble the parsed docstring from the collected state."""
    parsed = state.parsed
    parsed.description = "\n".join(state.description_lines).strip()
    parsed.returns = " ".join(state.returns_parts).strip()

    for info in parsed.params.values():
        info.required = bool(_REQUIRED_RE.search(info.description))

    return parsed


def _param_from_match(match: re.Match[str]) -> ParamInfo:
    """Build a :class:`ParamInfo` from a ``:param`` directive match."""
    head = match.group("head").strip()
    parts = head.split()
    name = parts[-1].lstrip("*") if parts else ""
    type_hint = " ".join(parts[:-1]).strip()

    return ParamInfo(
        name=name,
        type=type_hint,
        description=match.group("desc").strip(),
    )


def convert_module_to_method(module: str) -> str | None:
    """Map a core action module name to its HTTP method."""
    return MODULE_METHODS.get(module.lower())


def infer_method(name: str, func: Callable[..., Any]) -> str:
    """Guess the HTTP method of an action.

    Priority: an explicit ``apidocs_method`` attribute, the module the
    action is defined in, the ``side_effect_free`` marker and finally the
    action name itself.
    """
    explicit = getattr(func, APIDOCS_METHOD_ATTR, None)
    if isinstance(explicit, str) and explicit.upper() in config.DEFAULT_METHODS:
        return explicit.upper()

    module = func.__module__.rsplit(".", 1)[-1]
    if method := convert_module_to_method(module):
        return method

    if getattr(func, "side_effect_free", False):
        return "GET"

    if name.startswith(GET_NAME_PREFIXES) or name.endswith(GET_NAME_SUFFIXES):
        return "GET"

    return FALLBACK_METHOD


def collect_actions(
    include_extensions: Sequence[str] | None = None,
    exclude_extensions: Sequence[str] | None = None,
) -> dict[str, ActionInfo]:
    """Collect API actions from CKAN core and from the enabled plugins.

    Returns a mapping of ``action_name -> ActionInfo``, sorted by name.
    Plugins listed in ``exclude_extensions`` (or missing from a non-empty
    ``include_extensions``) are skipped. Plugins raising exceptions during
    discovery are logged and skipped, never silently swallowed.
    """
    actions = _collect_core_actions()

    included = _normalize(include_extensions)
    excluded = _normalize(exclude_extensions)

    for plugin in p.PluginImplementations(p.IActions):
        if not _is_selected(plugin, included, excluded):
            continue

        origin, plugin_actions = _collect_plugin_actions(plugin)

        for name, func in plugin_actions.items():
            actions[name] = _merge_plugin_action(
                actions.get(name), name, func, origin
            )

    return dict(sorted(actions.items()))


def _collect_core_actions() -> dict[str, ActionInfo]:
    """Actions defined by CKAN itself, keyed by action name."""
    actions: dict[str, ActionInfo] = {}

    for module_name in CORE_ACTION_MODULES:
        module = importlib.import_module(f"ckan.logic.action.{module_name}")

        for name, func in authz.get_local_functions(module):
            actions[name] = ActionInfo(
                name=name,
                func=func,
                method=infer_method(name, func),
                origin=CORE_ORIGIN,
                module=module_name,
                chained=bool(getattr(func, "chained_action", False)),
                side_effect_free=bool(getattr(func, "side_effect_free", False)),
            )

    return actions


def _is_selected(
    plugin: Any, included: set[str], excluded: set[str]
) -> bool:
    """Whether a plugin passes the extension include/exclude filters."""
    identifiers = _plugin_identifiers(plugin)

    if excluded and identifiers & excluded:
        log.debug("Skipping actions of excluded plugin %s", identifiers)
        return False

    return not included or bool(identifiers & included)


def _collect_plugin_actions(
    plugin: Any,
) -> tuple[str, dict[str, Callable[..., Any]]]:
    """Collect the usable actions of a single plugin.

    Returns the name the plugin is tagged with together with its actions.
    A plugin that cannot provide them is logged and reported as empty, so
    it never breaks the whole document.
    """
    identifiers = _plugin_identifiers(plugin)
    origin = getattr(plugin, "name", None) or min(identifiers)

    try:
        plugin_actions = plugin.get_actions()
    except Exception:
        log.exception(
            "Failed to collect actions from plugin %s",
            ", ".join(sorted(identifiers)),
        )
        return origin, {}

    if not plugin_actions:
        return origin, {}

    if not isinstance(plugin_actions, dict):
        log.warning(
            "Plugin %s returned actions of unexpected type %s",
            ", ".join(sorted(identifiers)),
            type(plugin_actions).__name__,
        )
        return origin, {}

    selected: dict[str, Callable[..., Any]] = {}

    for name, func in plugin_actions.items():
        if not callable(func):
            log.warning(
                "Plugin %s returned a non-callable action %r",
                origin,
                name,
            )
            continue

        selected[name] = func

    return origin, selected


def _merge_plugin_action(
    previous: ActionInfo | None,
    name: str,
    func: Callable[..., Any],
    origin: str,
) -> ActionInfo:
    """Build the entry of a plugin action, shadowing any existing one.

    A plugin action that overrides a core or chained action keeps the
    ``chained`` marker of the action it replaces.
    """
    chained = bool(getattr(func, "chained_action", False))

    if previous is not None:
        chained = chained or previous.chained

    return ActionInfo(
        name=name,
        func=func,
        method=infer_method(name, func),
        origin=origin,
        module=func.__module__.split(".")[-1],
        chained=chained,
        side_effect_free=bool(getattr(func, "side_effect_free", False)),
    )


def get_api_methods() -> list[dict[str, Any]]:
    """Details of the HTTP methods enabled in the configuration."""
    allowed = config.apidocs_allowed_api_methods()
    return [
        method for method in config.API_METHODS if method["name"] in allowed
    ]


def _plugin_identifiers(plugin: Any) -> set[str]:
    """Names a plugin can be referenced by in the configuration."""
    identifiers: set[str] = set()

    if name := getattr(plugin, "name", None):
        identifiers.add(str(name).lower())

    module = type(plugin).__module__
    if module.startswith("ckanext."):
        identifiers.add(module.split(".", 2)[1].lower())

    identifiers.add(type(plugin).__name__.lower())

    return identifiers


def _normalize(values: Sequence[str] | None) -> set[str]:
    if not values:
        return set()

    return {str(value).strip().lower() for value in values if str(value).strip()}
