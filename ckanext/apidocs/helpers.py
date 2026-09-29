"""Building, caching and serializing the OpenAPI document."""

from __future__ import annotations

import copy
import hashlib
import json
import logging
import time
from collections.abc import Sequence
from typing import Any

from sqlalchemy.exc import DBAPIError, UnboundExecutionError

from ckan import model as ckan_model
from ckan import plugins as p

from ckanext.apidocs import config, interfaces, model
from ckanext.apidocs.schemas import schema
from ckanext.apidocs.utils import actions, docstring

try:
    import yaml
except ImportError:  # pragma: no cover - optional dependency
    yaml = None  # type: ignore[assignment]


log = logging.getLogger(__name__)

CKAN_VERSION = config.CKAN_VERSION

_cache: tuple[str, float, dict[str, Any]] | None = None


def build_openapi_spec(
    *,
    base_path: str | None = None,
    version: str | None = None,
    title: str | None = None,
    description: str | None = None,
    methods: Sequence[str] | None = None,
    token_header: str | None = None,
    include_extensions: Sequence[str] | None = None,
    exclude_extensions: Sequence[str] | None = None,
) -> dict[str, Any]:
    """Build an OpenAPI specification describing the available actions.

    Every argument defaults to the corresponding configuration setting, read
    at call time, so the caller can override individual values (the CLI does
    exactly that). The returned document is always a fresh object.
    """
    allowed_methods = list(
        methods or config.apidocs_allowed_api_methods()
    )

    if include_extensions is None:
        include_extensions = config.apidocs_included_extensions()
    if exclude_extensions is None:
        exclude_extensions = config.apidocs_excluded_extensions()

    spec = schema.build_spec(
        base_path=base_path,
        openapi_version=config.apidocs_openapi_version(),
        title=title,
        description=description,
        version=version,
        methods=allowed_methods,
        token_header=token_header,
    )

    discovered = actions.collect_actions(
        include_extensions=include_extensions,
        exclude_extensions=exclude_extensions,
    )

    for action_name, info in discovered.items():
        if action_name.startswith("_"):
            continue

        if info.method not in allowed_methods:
            continue

        parsed = docstring.parse_docstring(info.func.__doc__)
        operation = _build_operation(action_name, info, parsed)

        paths = spec["paths"].setdefault(f"/{action_name}", {})
        paths[info.method.lower()] = operation

    return _apply_spec_extensions(spec)


def get_stored_schema() -> model.ApidocsSchema | None:
    """The OpenAPI document stored by a sysadmin, if any.

    A database that is unreachable, or that does not have the extension
    tables yet, is reported as "nothing stored": serving the documentation
    must not depend on the database being migrated.
    """
    try:
        with ckan_model.Session.begin_nested():
            return model.ApidocsSchema.get()
    except (DBAPIError, UnboundExecutionError):
        log.debug("cannot read the apidocs_schema table")
        return None


def get_openapi_spec(*, force: bool = False) -> dict[str, Any]:
    """Return the specification, using the configured cache when possible.

    The document stored by a sysadmin (see the ``apidocs_admin`` views) is
    served instead of the generated one, with its object keys in alphabetical
    order, see :func:`ckanext.apidocs.utils.ordering.canonical_definition`. The
    cache is keyed on the settings that affect the generated document and on
    the version of the stored one, so a save is picked up by every worker
    process without waiting for the TTL to expire. The cache expires after
    ``ckanext.apidocs.cache_ttl`` seconds; a TTL of zero disables caching
    entirely. The returned document is a copy, so callers are free to modify
    it.
    """
    global _cache

    ttl = config.apidocs_cache_ttl()
    key = _cache_key(_stored_schema_fingerprint())

    if not force and ttl > 0 and _cache is not None:
        cached_key, expires_at, cached_spec = _cache
        if cached_key == key and expires_at > time.monotonic():
            return copy.deepcopy(cached_spec)

    stored = get_stored_schema()
    spec = (
        stored.canonical_definition
        if stored is not None
        else build_openapi_spec()
    )
    _cache = (key, time.monotonic() + ttl, spec)

    return copy.deepcopy(spec)


def invalidate_cache() -> None:
    """Drop the cached specification, if any."""
    global _cache
    _cache = None


def _stored_schema_fingerprint() -> str | None:
    """Cheap change marker of the stored document.

    Reading the version counter costs a single lookup of a tiny row, while
    the document itself can be large, so the fingerprint is what the cache is
    keyed on. ``None`` means "cannot tell" (no database or no tables), which
    keeps the cache usable and makes every call fall back to the generated
    document.
    """
    try:
        with ckan_model.Session.begin_nested():
            version, updated = model.ApidocsSchemaState.fingerprint()
    except (DBAPIError, UnboundExecutionError):
        log.debug("cannot read the apidocs_schema_state table")
        return None

    return f"{version}@{updated.isoformat() if updated else ''}"


def dumps_openapi_json(spec: dict[str, Any]) -> str:
    """Serialize the specification as pretty printed JSON."""
    return json.dumps(spec, indent=2)


def dump_openapi_yaml(spec: dict[str, Any]) -> str:
    """Serialize the specification as YAML."""
    if yaml is None:  # pragma: no cover - optional dependency
        log.warning(
            "PyYAML is not installed, returning the specification as JSON"
        )
        return dumps_openapi_json(spec)

    return yaml.safe_dump(
        spec, sort_keys=False, allow_unicode=True, default_flow_style=False
    )


def spec_etag(payload: str) -> str:
    """Return the ETag (unquoted) of a serialized specification."""
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def collect_badges(spec: dict[str, Any]) -> dict[str, dict[str, list[str]]]:
    """Index the ``x-badges`` of every operation by path and method.

    The result is embedded into the page configuration so the browser does
    not have to fetch and inspect the specification again.
    """
    badges: dict[str, dict[str, list[str]]] = {}

    for path, operations in spec.get("paths", {}).items():
        for method, operation in operations.items():
            values = operation.get("x-badges")
            if values:
                badges.setdefault(path, {})[method] = list(values)

    return badges


def _build_operation(
    action_name: str, info: actions.ActionInfo, parsed: docstring.ParsedDocstring
) -> dict[str, Any]:
    badges = info.badges()
    badges.extend(_interface_badges(action_name, info.origin))

    kwargs: dict[str, Any] = {}
    if info.method == "GET":
        kwargs["parameters"] = schema.build_parameters(parsed.params_dict())
    else:
        kwargs["request_body"] = schema.build_request_body(
            parsed.params_dict()
        )

    external_docs = None
    if info.origin == actions.CORE_ORIGIN and info.module:
        external_docs = schema.core_action_external_docs(
            info.module, action_name, CKAN_VERSION
        )

    return schema.build_operation(
        method=info.method,
        summary=parsed.summary or action_name,
        operation_id=action_name,
        description=_compose_description(parsed),
        badges=badges,
        external_docs=external_docs,
        **kwargs,
    )


def _compose_description(parsed: docstring.ParsedDocstring) -> str:
    chunks = [parsed.description] if parsed.description else []

    if parsed.returns and parsed.returns_type:
        returns = f"{parsed.returns} ({parsed.returns_type})"
    elif parsed.returns:
        returns = parsed.returns
    elif parsed.returns_type:
        returns = parsed.returns_type
    else:
        returns = ""

    if returns:
        chunks.append(f"**Returns:** {returns}")

    return "\n\n".join(chunks)


def _interface_badges(action_name: str, origin: str) -> list[str]:
    badges: list[str] = []

    for plugin in p.PluginImplementations(interfaces.IApidocs):
        try:
            extra = plugin.get_action_badges(action_name, origin)
        except Exception:
            log.exception(
                "IApidocs.get_action_badges failed for action %s", action_name
            )
            continue

        if extra:
            badges.extend(str(badge) for badge in extra)

    return badges


def _apply_spec_extensions(spec: dict[str, Any]) -> dict[str, Any]:
    """Let ``IApidocs`` implementations adjust the generated document."""
    for plugin in p.PluginImplementations(interfaces.IApidocs):
        try:
            result = plugin.modify_openapi_spec(spec)
        except Exception:
            log.exception(
                "IApidocs.modify_openapi_spec failed for plugin %s",
                getattr(plugin, "name", type(plugin).__name__),
            )
            continue

        if result is not None:
            spec = result

    return spec


def _cache_key(fingerprint: str | None = None) -> str:
    parts = [
        str(fingerprint),
        config.apidocs_base_path(),
        config.apidocs_openapi_version(),
        config.apidocs_title(),
        config.apidocs_description(),
        config.apidocs_spec_version(),
        config.apidocs_token_header(),
        ",".join(config.apidocs_allowed_api_methods()),
        ",".join(config.apidocs_included_extensions()),
        ",".join(config.apidocs_excluded_extensions()),
    ]

    return "|".join(parts)
