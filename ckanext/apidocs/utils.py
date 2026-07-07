import importlib
import re
from typing import Any, Dict, List, Optional, Tuple

import ckan.plugins as p
from ckan.logic import authz

from ckanext.apidocs import config


def parse_docstring(doc: Optional[str]) -> Tuple[str, str, Dict[str, Dict[str, str]]]:
    """Parse a ReST style CKAN docstring.

    Returns (summary, description, params) where params maps param name to
    {"type": ..., "description": ...}
    """
    if not doc:
        return "", "", {}
    lines = [line.rstrip() for line in doc.splitlines()]
    summary = ""
    description_lines: List[str] = []
    params: Dict[str, Dict[str, str]] = {}

    in_params = False
    in_results = False
    for line in lines:
        strip = line.strip()
        if not strip:
            if summary and not in_params:
                description_lines.append("")
            continue
        if not summary:
            summary = strip
            continue

        # Parameter parsing
        if strip.startswith(":param ") and not in_results:
            in_params = True
            try:
                rest = strip[len(":param "):]
                name, desc = rest.split(":", 1)

                # Extract the parameter name from the line removing any type hints
                match = re.search(r'(\w+)$', name)
                if match:
                    name = match.group(1)

                params[name.strip()] = params.get(name.strip(), {})
                params[name.strip()]["description"] = desc.strip()
            except ValueError:
                pass
            continue

        if strip.startswith(":type ") and not in_results:
            in_params = True
            try:
                rest = strip[len(":type "):]
                name, typ = rest.split(":", 1)
                params[name.strip()] = params.get(name.strip(), {})
                params[name.strip()]["type"] = typ.strip()
                in_params = False
            except ValueError:
                pass
            continue
        
        if strip.startswith("Note:") or strip.startswith(".. note::"):
            in_params = False
            in_results = True
            line = strip.replace(".. note:", "**Note**")

        if strip.startswith(":return"):
            in_params = False
            in_results = True
            line = strip.replace(":returns", "**Returns**").replace(":return", "**Returns**")

        if strip.startswith(":rtype"):
            in_params = False
            in_results = True
            line = "\n" + strip.replace(":rtype", "**Return type**")

        if strip.startswith(":raises"):
            in_params = False
            in_results = True
            line = strip.replace(":raises", "**Raises**")

        if in_params:
            # Continuation of param description
            if params:
                last_param = list(params.keys())[-1]
                params[last_param]["description"] += " " + strip
            continue

        if not in_params:
            description_lines.append(line)

    description = "\n".join(description_lines).strip()

    return summary, description, params #, returns


def convert_module_to_method(module: str) -> str | None:
    """Convert module name to HTTP method."""
    method_map = {
        "get": "GET",
        "create": "POST",
        "update": "PUT",
        "patch": "PATCH",
        "delete": "DELETE",
    }
    return method_map.get(module.lower())


def collect_actions() -> Dict[str, Any]:
    """Collect all CKAN API actions from core and plugin modules.

    Returns a dictionary mapping action_name -> function object.
    """
    actions: Dict[str, Any] = {}

    # Import core logic action modules and inspect their functions
    for module_name in ["get", "create", "update", "patch", "delete"]:
        module = importlib.import_module(f"ckan.logic.action.{module_name}")
        for name, func in authz.get_local_functions(module):
            setattr(func, "__origin__", "core")
            actions[name] = func
                
    # Also include actions registered in plugins
    for plugin in p.PluginImplementations(p.IActions):
        try:
            if plugin_actions := plugin.get_actions():
                for name, func in plugin_actions.items():
                    setattr(func, "__origin__", plugin.name)
                    
                    if name in actions and getattr(actions[name], "chained_action", None):
                        setattr(func, "chained_action", True)

                actions.update(plugin_actions)
        except Exception:
            # Ignore extensions that misbehave during discovery
            continue

    return dict(sorted(actions.items()))


def get_api_methods() -> List[dict[str, Any]]:
    """Get the details of allowed API methods."""
    allowed_api_methods = config.apidocs_allowed_api_methods()
    api_methods = config.API_METHODS

    return [method for method in api_methods if method.get("name") in allowed_api_methods]
