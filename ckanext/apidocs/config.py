from __future__ import annotations

import ckan.plugins.toolkit as tk


APIDOCS_ALLOWED_API_METHODS = "ckanext.apidocs.enable_api_methods"
APIDOCS_BASE_PATH = "ckanext.apidocs.base_path"
APIDOCS_OPENAPI_VERSION = "ckanext.apidocs.openapi_version"

API_METHODS = [
    {"name": "GET", "description": "API functions for searching for and getting data from CKAN"},
    {"name": "POST", "description": "API functions for adding data to CKAN"},
    {"name": "PUT", "description": "API functions for updating existing data in CKAN"},
    {"name": "PATCH", "description": "API functions for partial updates of existing data in CKAN"},
    {"name": "DELETE", "description": "API functions for deleting data from CKAN"},
]


def apidocs_base_path() -> str:
    base_path = tk.config.get(APIDOCS_BASE_PATH)
    return base_path if base_path else "/api/3/action"


def apidocs_allowed_api_methods() -> list[str]:
    methods = tk.aslist(tk.config.get(APIDOCS_ALLOWED_API_METHODS, "").upper())
    return methods if methods else ["GET", "POST", "PUT", "PATCH", "DELETE"]


def apidocs_openapi_version() -> str:
    openapi_version = tk.config.get(APIDOCS_OPENAPI_VERSION)
    return openapi_version if openapi_version else "3.0.0"
