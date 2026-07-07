from typing import Any, Dict

try:
    import yaml
except Exception:
    yaml = None

import ckan

from ckanext.apidocs import config, utils
from ckanext.apidocs.schemas import schema


CKAN_VERSION = ckan.__version__.rsplit('.', 1)[0]


def build_openapi_spec() -> Dict[str, Any]:
    """Build an OpenAPI spec (as a Python dict) describing CKAN actions.

    This is intentionally conservative: it parses docstrings to create
    parameter lists and simple schemas for request bodies.
    """
    actions = utils.collect_actions()

    spec = schema.spec.copy()

    for action_name, func in actions.items():
        # Skip private / internal actions
        if action_name.startswith("_"):
            continue
        
        module = func.__module__.split(".")[-1]
        method = utils.convert_module_to_method(module)
        if method is None:
            method = "GET" if getattr(func, "side_effect_free", False) else "POST"
        if method not in config.apidocs_allowed_api_methods():
            continue

        badges = []
        if origin := getattr(func, "__origin__", None):
            badges.append(origin)
        if getattr(func, "chained_action", False):
            badges.append("chained")

        summary, description, params = utils.parse_docstring(func.__doc__)

        # Build path and operation
        path = f"/{action_name}"
        operation = schema.operation.copy()
        operation["tags"] = [method]
        operation["summary"] = summary or action_name
        operation["x-badges"] = badges
        operation["description"] = description

        if origin == "core":
            operation["externalDocs"] = {
                "url": f"https://docs.ckan.org/en/{CKAN_VERSION}/api/index.html#ckan.logic.action.{module}.{action_name}"
            }

        # Build parameters or requestBody
        if method == "GET":
            # map params to query parameters
            parameters = []
            for param_name, param_info in params.items():
                param_schema: Dict[str, Any] = {"type": "string"}
                param_type = param_info.get("type", "")
                if "int" in param_type or "int" in param_type.lower():
                    param_schema["type"] = "integer"
                elif "bool" in param_type.lower():
                    param_schema["type"] = "boolean"
                elif "list" in param_type.lower() or "list of" in param_type.lower():
                    param_schema = {"type": "array", "items": {"type": "string"}}
                parameters.append({
                    "name": param_name,
                    "in": "query",
                    "required": False,
                    "schema": param_schema,
                    "description": param_info.get("description", ""),
                })
            operation["parameters"] = parameters
        else:
            # requestBody with JSON schema
            properties = {}
            for param_name, param_info in params.items():
                param_type = param_info.get("type", "")
                if "int" in param_type or "int" in param_type.lower():
                    param_schema = {"type": "integer"}
                elif "bool" in param_type.lower():
                    param_schema = {"type": "boolean"}
                elif "list" in param_type.lower() or "list of" in param_type.lower():
                    param_schema = {"type": "array", "items": {"type": "string"}}
                else:
                    param_schema = {"type": "string"}
                param_schema["description"] = param_info.get("description", "")
                properties[param_name] = param_schema
            operation["requestBody"] = {
                "content": {
                    "application/json": {"schema": {"type": "object", "properties": properties}},
                    "application/x-www-form-urlencoded": {"schema": {"type": "object", "properties": properties}},
                }
            }
            operation["security"] = [{"ApiKeyAuth": []}]
        spec["paths"].setdefault(path, {})[method.lower()] = operation

    return spec


def dump_openapi_yaml(spec: Dict[str, Any]) -> str:
    if yaml is None:  # pragma: no cover - fallback
        import json
        return json.dumps(spec, indent=2)
    return yaml.safe_dump(spec, sort_keys=False)
