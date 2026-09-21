"""OpenAPI document, operation and component factories.

Nothing in this module keeps mutable module level state: every public
function returns freshly built objects, so generating the specification
more than once (for example after a configuration change) can never leak
data between the calls.
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from ckanext.apidocs import config as apidocs_config


DOCS_BASE_URL = "https://docs.ckan.org/en/{version}/api/index.html"
SUCCESS_DESCRIPTION = "Successful response"
ERROR_SCHEMA_REF = "#/components/schemas/Error"

ERROR_RESPONSES: dict[str, str] = {
    "400": "Bad request - the parameters sent are invalid",
    "401": "Unauthorized - an API token is required",
    "403": "Forbidden - the user is not allowed to perform this action",
    "404": "Not found - the requested object does not exist",
}


def api_token_schema() -> dict[str, Any]:
    """Schema of the ``api_token_create`` result."""
    return {
        "type": "object",
        "properties": {
            "id": {
                "type": "string",
                "example": "rD7p2jJ7tLXtudlv0cO9BBjPLBwSXG4-WrEwGlGJUc0",
            },
            "name": {"type": "string", "example": "testapi"},
            "user_id": {
                "type": "string",
                "example": "11928daa-1864-4fe9-9571-91155db317d2",
            },
            "created_at": {
                "type": "string",
                "example": "2026-01-03T20:59:47.740897",
            },
            "last_access": {"type": "string", "example": "null"},
        },
    }


def error_schema() -> dict[str, Any]:
    """Schema of a CKAN error response."""
    return {
        "type": "object",
        "properties": {
            "help": {
                "type": "string",
                "description": "URL of the error documentation",
            },
            "success": {"type": "boolean", "example": False},
            "error": {
                "type": "object",
                "properties": {
                    "message": {"type": "string"},
                    "type": {"type": "string"},
                    "__type": {"type": "string"},
                },
            },
        },
    }


def success_schema() -> dict[str, Any]:
    """Schema of a successful CKAN action response."""
    return {
        "type": "object",
        "properties": {
            "help": {"type": "string"},
            "success": {"type": "boolean", "example": True},
            "result": {
                "description": "Result of the action, its shape depends on "
                "the action itself",
            },
        },
    }


def security_schemes(token_header: str) -> dict[str, Any]:
    """Security schemes supported by CKAN."""
    return {
        "ApiKeyAuth": {
            "type": "apiKey",
            "in": "header",
            "name": token_header,
            "description": "Paste your CKAN API key here (found on your user "
            f"profile). The key will be sent in the {token_header} header "
            "without any prefix.",
        }
    }


def build_components(token_header: str) -> dict[str, Any]:
    """Reusable components of the specification."""
    return {
        "schemas": {
            "APIToken": api_token_schema(),
            "Error": error_schema(),
        },
        "securitySchemes": security_schemes(token_header),
    }


def build_info(*, title: str, description: str, version: str) -> dict[str, Any]:
    return {
        "title": title,
        "description": description,
        "version": version,
    }


def build_external_docs(ckan_version: str) -> dict[str, str]:
    return {
        "description": "Find out more about CKAN API",
        "url": DOCS_BASE_URL.format(version=ckan_version) + "#api-guide",
    }


def build_tags(methods: Sequence[str], ckan_version: str) -> list[dict[str, Any]]:
    """Tags used to group operations, one per enabled HTTP method."""
    descriptions = {
        method["name"]: method["description"]
        for method in apidocs_config.API_METHODS
    }

    return [
        {
            "name": method,
            "description": descriptions.get(method, ""),
            "externalDocs": build_external_docs(ckan_version)
            | {
                "description": "Find out more",
                "url": DOCS_BASE_URL.format(version=ckan_version)
                + f"#module-ckan.logic.action.{method.lower()}",
            },
        }
        for method in methods
    ]


def core_action_external_docs(
    module: str, action_name: str, ckan_version: str
) -> dict[str, str]:
    """Link to the reference documentation of a core CKAN action."""
    return {
        "url": DOCS_BASE_URL.format(version=ckan_version)
        + f"#ckan.logic.action.{module}.{action_name}"
    }


def build_spec(
    *,
    base_path: str | None = None,
    openapi_version: str | None = None,
    title: str | None = None,
    description: str | None = None,
    version: str | None = None,
    methods: Sequence[str] | None = None,
    token_header: str | None = None,
) -> dict[str, Any]:
    """Build an empty OpenAPI document, ready to be filled with paths.

    All arguments default to the corresponding configuration settings, read
    at call time.
    """
    base_path = base_path or apidocs_config.apidocs_base_path()
    openapi_version = (openapi_version or apidocs_config.apidocs_openapi_version())
    title = title or apidocs_config.apidocs_title()
    description = description or apidocs_config.apidocs_description()
    version = version or apidocs_config.apidocs_spec_version()
    methods = list(methods or apidocs_config.apidocs_allowed_api_methods())
    token_header = token_header or apidocs_config.apidocs_token_header()
    ckan_version = apidocs_config.CKAN_VERSION

    return {
        "openapi": openapi_version,
        "info": build_info(title=title, description=description, version=version),
        "externalDocs": build_external_docs(ckan_version),
        "servers": [{"url": base_path}],
        "tags": build_tags(methods, ckan_version),
        "paths": {},
        "components": build_components(token_header),
    }


def build_responses() -> dict[str, Any]:
    """Default responses shared by every operation."""
    responses: dict[str, Any] = {
        "200": {
            "description": SUCCESS_DESCRIPTION,
            "content": {
                "application/json": {"schema": success_schema()},
            },
        }
    }

    for status, description in ERROR_RESPONSES.items():
        responses[status] = {
            "description": description,
            "content": {
                "application/json": {
                    "schema": {"$ref": ERROR_SCHEMA_REF},
                },
            },
        }

    return responses


def build_operation(
    *,
    method: str,
    summary: str,
    operation_id: str,
    description: str = "",
    parameters: list[dict[str, Any]] | None = None,
    request_body: dict[str, Any] | None = None,
    badges: Sequence[str] | None = None,
    external_docs: Mapping[str, str] | None = None,
    security: bool = True,
) -> dict[str, Any]:
    """Build a single OpenAPI operation object."""
    operation: dict[str, Any] = {
        "tags": [method],
        "summary": summary,
        "operationId": operation_id,
        "description": description,
        "responses": build_responses(),
    }

    if parameters:
        operation["parameters"] = parameters

    if request_body:
        operation["requestBody"] = request_body

    if badges:
        operation["x-badges"] = list(badges)

    if external_docs:
        operation["externalDocs"] = dict(external_docs)

    if security:
        operation["security"] = [{"ApiKeyAuth": []}]

    return operation


def schema_from_type(type_hint: str | None) -> dict[str, Any]:
    """Turn a docstring type hint into a JSON schema fragment."""
    hint = (type_hint or "").lower()

    if not hint:
        return {"type": "string"}

    is_list = any(
        marker in hint for marker in ("list", "array", "[]", "sequence")
    )
    item_hint = hint.replace("list of", "").replace("list", "")
    item_hint = item_hint.replace("array", "").replace("[]", "")

    if is_list:
        return {"type": "array", "items": _scalar_schema(item_hint)}

    if "dict" in hint or "mapping" in hint or "object" in hint:
        return {"type": "object"}

    return _scalar_schema(hint)


def _scalar_schema(hint: str) -> dict[str, Any]:
    if "int" in hint:
        return {"type": "integer"}

    if "bool" in hint:
        return {"type": "boolean"}

    if "float" in hint or "number" in hint or "decimal" in hint:
        return {"type": "number"}

    return {"type": "string"}


def build_parameters(
    params: Mapping[str, Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Build query parameters for a GET operation."""
    return [
        {
            "name": name,
            "in": "query",
            "required": bool(info.get("required")),
            "schema": schema_from_type(info.get("type")),
            "description": info.get("description", ""),
        }
        for name, info in params.items()
    ]


def build_request_body(
    params: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    """Build the request body of a non-GET operation."""
    properties = {}
    required = []

    for name, info in params.items():
        schema = schema_from_type(info.get("type"))
        if info.get("description"):
            schema["description"] = info["description"]

        properties[name] = schema

        if info.get("required"):
            required.append(name)

    body_schema: dict[str, Any] = {
        "type": "object",
        "properties": properties,
    }
    if required:
        body_schema["required"] = required

    return {
        "content": {
            "application/json": {"schema": body_schema},
            "application/x-www-form-urlencoded": {"schema": body_schema},
        }
    }
