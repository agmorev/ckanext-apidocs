"""Parsing of the action docstrings into a structured representation.

The parser understands the ReST directives CKAN uses to document an action
(``:param:``, ``:type:``, ``:returns:``, ``:rtype:``, ``:raises:`` and
``.. note::``), including their indented continuations and plain text
paragraphs. Malformed lines are ignored instead of producing garbage
descriptions.
"""

from __future__ import annotations

import inspect
import re
from dataclasses import dataclass, field
from typing import Any


__all__ = ["ParamInfo", "ParsedDocstring", "parse_docstring"]

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
