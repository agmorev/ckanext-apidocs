"""Canonical ordering of the OpenAPI document stored by sysadmins.

Two reasons make the ordering part of reading a document rather than only
part of writing one:

- the definition is stored in a ``JSONB`` column, and ``jsonb`` does not
  preserve the order the keys were stored in (it keeps them sorted by length
  first), so an order applied before saving would be gone after reading;
- sorting ``paths`` is what makes the documentation readable: the Swagger UI
  groups the operations into one section per HTTP method and lists each
  section in the order of ``paths``, so every method ends up alphabetical as
  well.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any


__all__ = ["canonical_definition"]


def canonical_definition(document: dict[str, Any]) -> dict[str, Any]:
    """Return a copy of ``document`` ordered alphabetically by object key.

    The keys of every object of the document are sorted, so the same content
    always has the same representation, and the operations of every HTTP
    method section of the documentation are alphabetical.

    Lists (``tags``, ``servers``, a list of ``parameters``, ...) keep their
    order, it is meaningful for the rendered documentation. The document
    passed in is never modified.
    """
    return dict(_ordered_items(document))


def _ordered_items(mapping: dict[str, Any]) -> Iterator[tuple[str, Any]]:
    for key, value in sorted(mapping.items()):
        yield key, _ordered_value(value)


def _ordered_value(value: Any) -> Any:
    if isinstance(value, dict):
        return dict(_ordered_items(value))

    if isinstance(value, list):
        return [_ordered_value(item) for item in value]

    return value
