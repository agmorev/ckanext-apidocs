"""Discovery of the API actions and of the HTTP method of each of them.

The module is deliberately free of side effects: unlike the previous
implementation it never mutates the discovered action functions, and all
failures coming from third party plugins are logged instead of being
silently ignored.
"""

from __future__ import annotations

import importlib
import logging
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any

from ckan import authz
from ckan import plugins as p

from ckanext.apidocs import config


__all__ = [
    "APIDOCS_METHOD_ATTR",
    "CORE_ACTION_MODULES",
    "CORE_ORIGIN",
    "MODULE_METHODS",
    "ActionInfo",
    "collect_actions",
    "convert_module_to_method",
    "get_api_methods",
    "infer_method",
]

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
