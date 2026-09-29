"""Validators and parsing helpers for the stored OpenAPI document.

A sysadmin can paste both JSON and YAML, so the document is parsed with
``json`` first and with YAML as a fallback. Only the structural part of the
OpenAPI specification that the documentation page relies on is checked: the
document has to be a mapping with ``openapi``, ``info`` (``title`` and
``version``) and ``paths``. Validating the full specification is left to the
Swagger UI validator configured with ``ckanext.apidocs.ui.validator_url``.
"""

from __future__ import annotations

import json
from typing import Any

import ckan.plugins.toolkit as tk
from ckan import types

try:
    import yaml
except ImportError:  # pragma: no cover - optional dependency
    yaml = None  # type: ignore[assignment]


# Only the validator is registered through the ``validators`` blanket, the
# helpers around it are imported by name.
__all__ = ["apidocs_definition_valid"]

#: Root keys the documentation page needs to render an OpenAPI document.
REQUIRED_KEYS = ("openapi", "info", "paths")


class InvalidDefinition(ValueError):
    """Raised when a document cannot be parsed or is not OpenAPI shaped."""

    def __init__(self, errors: list[str]):
        self.errors = errors
        super().__init__("; ".join(errors))


def parse_definition(value: Any) -> dict[str, Any]:
    """Parse a JSON or YAML OpenAPI document and check its structure.

    Raises:
        InvalidDefinition: the value cannot be parsed or required parts of
            the OpenAPI document are missing or malformed.
    """
    document = _parse_document(value)

    errors = _structure_errors(document)
    if errors:
        raise InvalidDefinition(errors)

    return document


def apidocs_definition_valid(
    key: types.FlattenKey,
    data: types.FlattenDataDict,
    errors: types.FlattenErrorDict,
    context: types.Context,
) -> None:
    """Validator replacing the posted document with the parsed one."""
    try:
        data[key] = parse_definition(data.get(key))
    except InvalidDefinition as err:
        raise tk.Invalid("; ".join(str(error) for error in err.errors)) from err


def _parse_document(value: Any) -> dict[str, Any]:
    """Turn a mapping, a JSON string or a YAML string into a mapping."""
    if isinstance(value, dict):
        return value

    if not isinstance(value, str) or not value.strip():
        raise InvalidDefinition(
            [tk._("The document must be a JSON or YAML object")]
        )

    try:
        return _as_mapping(json.loads(value), "JSON")
    except json.JSONDecodeError as json_error:
        return _parse_yaml(value, json_error)


def _parse_yaml(value: str, json_error: json.JSONDecodeError) -> dict[str, Any]:
    if yaml is None:  # pragma: no cover - optional dependency
        raise InvalidDefinition(
            [
                tk._("Could not parse the document as valid JSON: {}").format(
                    json_error
                )
            ]
        )

    try:
        data = yaml.safe_load(value)
    except yaml.YAMLError as yaml_error:
        raise InvalidDefinition(
            [
                tk._(
                    "Could not parse the document as valid JSON ({json}) or "
                    "YAML ({yaml})"
                ).format(json=json_error, yaml=yaml_error)
            ]
        ) from yaml_error

    return _as_mapping(data, "YAML")


def _as_mapping(data: Any, kind: str) -> dict[str, Any]:
    if not isinstance(data, dict):
        raise InvalidDefinition(
            [
                tk._("The document must be a {kind} object").format(kind=kind)
            ]
        )

    return data


def _structure_errors(document: dict[str, Any]) -> list[str]:
    errors: list[str] = []

    for key in REQUIRED_KEYS:
        if key not in document:
            errors.append(tk._("Missing required key: {key}").format(key=key))

    errors.extend(_openapi_errors(document))
    errors.extend(_info_errors(document))
    errors.extend(_paths_errors(document))

    return errors


def _openapi_errors(document: dict[str, Any]) -> list[str]:
    if "openapi" not in document:
        return []

    version = document["openapi"]

    if not isinstance(version, str) or not version.strip():
        return [tk._("'openapi' must be a non-empty string")]

    if not version.startswith("3."):
        return [
            tk._(
                "'openapi' must be an OpenAPI 3.x version, got '{version}'"
            ).format(version=version)
        ]

    return []


def _info_errors(document: dict[str, Any]) -> list[str]:
    if "info" not in document:
        return []

    info = document["info"]

    if not isinstance(info, dict):
        return [tk._("'info' must be an object")]

    errors: list[str] = []

    for key in ("title", "version"):
        value = info.get(key)

        if not isinstance(value, str) or not value.strip():
            errors.append(
                tk._("'info.{key}' must be a non-empty string").format(key=key)
            )

    return errors


def _paths_errors(document: dict[str, Any]) -> list[str]:
    if "paths" not in document:
        return []

    paths = document["paths"]

    if not isinstance(paths, dict):
        return [tk._("'paths' must be an object")]

    return [
        tk._("Path '{path}' must start with '/'").format(path=path)
        for path in paths
        if not str(path).startswith(("/", "x-"))
    ]
