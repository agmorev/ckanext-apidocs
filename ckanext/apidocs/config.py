"""Configuration accessors for ckanext-apidocs.

Every accessor reads the CKAN configuration lazily, at call time, so that
changes made after the extension module has been imported (tests, ``ckan.ini``
overrides, config declarations) are always respected.
"""

from __future__ import annotations

from typing import Any

from ckan import __version__ as ckan_version
from ckan.plugins import toolkit as tk


APIDOCS_BASE_PATH = "ckanext.apidocs.base_path"
APIDOCS_OPENAPI_VERSION = "ckanext.apidocs.openapi_version"
APIDOCS_ALLOWED_API_METHODS = "ckanext.apidocs.enable_api_methods"
APIDOCS_TITLE = "ckanext.apidocs.title"
APIDOCS_DESCRIPTION = "ckanext.apidocs.description"
APIDOCS_SPEC_VERSION = "ckanext.apidocs.spec_version"
APIDOCS_TOKEN_HEADER = "ckanext.apidocs.token_header"
APIDOCS_CACHE_TTL = "ckanext.apidocs.cache_ttl"
APIDOCS_REQUIRE_LOGIN = "ckanext.apidocs.require_login"
APIDOCS_SYSADMIN_ONLY = "ckanext.apidocs.sysadmin_only"
APIDOCS_ALLOWED_USERS = "ckanext.apidocs.allowed_users"
APIDOCS_INCLUDE_EXTENSIONS = "ckanext.apidocs.include_extensions"
APIDOCS_EXCLUDE_EXTENSIONS = "ckanext.apidocs.exclude_extensions"

APIDOCS_UI_VALIDATOR_URL = "ckanext.apidocs.ui.validator_url"
APIDOCS_UI_PERSIST_AUTHORIZATION = "ckanext.apidocs.ui.persist_authorization"
APIDOCS_UI_DOC_EXPANSION = "ckanext.apidocs.ui.doc_expansion"
APIDOCS_UI_FILTER = "ckanext.apidocs.ui.filter"
APIDOCS_UI_TRY_IT_OUT = "ckanext.apidocs.ui.try_it_out"
APIDOCS_UI_DEEP_LINKING = "ckanext.apidocs.ui.deep_linking"


CKAN_VERSION = ckan_version.rsplit(".", 1)[0]
CKAN_FULL_VERSION = ckan_version

DEFAULT_BASE_PATH = "/api/3/action"
DEFAULT_OPENAPI_VERSION = "3.0.0"
OPENAPI_VERSIONS = ("3.0.0", "3.0.1", "3.0.2", "3.0.3", "3.0.4", "3.1.0")
DEFAULT_DOC_EXPANSION = "list"
DOC_EXPANSION_VALUES = ("none", "list", "full")
DEFAULT_CACHE_TTL = 300
DEFAULT_TOKEN_HEADER = "Authorization"
DEFAULT_UI_VALIDATOR_URL = ""

API_METHODS: list[dict[str, str]] = [
    {
        "name": "GET",
        "description": "API functions for searching for and getting data from CKAN",
    },
    {
        "name": "POST",
        "description": "API functions for adding data to CKAN",
    },
    {
        "name": "PUT",
        "description": "API functions for updating existing data in CKAN",
    },
    {
        "name": "PATCH",
        "description": "API functions for partial updates of existing data in CKAN",
    },
    {
        "name": "DELETE",
        "description": "API functions for deleting data from CKAN",
    },
]

DEFAULT_METHODS = [method["name"] for method in API_METHODS]

DEFAULT_DESCRIPTION = (
    "This is the API documentation for CKAN. CKAN's Action API is a "
    "powerful, RPC-style API that exposes all of CKAN's core features to "
    "API clients. All of a CKAN website's core functionality (everything "
    "you can do with the web interface and more) can be used by external "
    "code that calls the CKAN API. It provides the option of using the "
    "[OpenAPI](https://spec.openapis.org/oas/v{openapi_version}) and is "
    "developed on top of the [Swagger UI]"
    "(https://github.com/swagger-api/swagger-ui)."
)


def apidocs_base_path() -> str:
    """The server URL prefix used for the documented action endpoints."""
    value = tk.config.get(APIDOCS_BASE_PATH)
    if not value:
        return DEFAULT_BASE_PATH

    value = str(value).rstrip("/")
    return value or "/"


def apidocs_openapi_version() -> str:
    """The OpenAPI specification version advertised in the document."""
    value = tk.config.get(APIDOCS_OPENAPI_VERSION)
    if value in OPENAPI_VERSIONS:
        return str(value)

    return DEFAULT_OPENAPI_VERSION


def apidocs_allowed_api_methods() -> list[str]:
    """HTTP methods that are included in the generated specification."""
    raw = tk.config.get(APIDOCS_ALLOWED_API_METHODS)
    if not raw:
        return list(DEFAULT_METHODS)

    requested = [str(item).strip().upper() for item in tk.aslist(raw)]
    methods = [method for method in requested if method in DEFAULT_METHODS]

    if len(methods) != len(requested) or not methods:
        return list(DEFAULT_METHODS)

    return methods


def apidocs_title() -> str:
    """Title of the generated API documentation."""
    return str(tk.config.get(APIDOCS_TITLE) or "CKAN API")


def apidocs_description() -> str:
    """Long description shown at the top of the API documentation."""
    value = tk.config.get(APIDOCS_DESCRIPTION)
    if value:
        return str(value)

    return DEFAULT_DESCRIPTION.format(
        openapi_version=apidocs_openapi_version()
    )


def apidocs_spec_version() -> str:
    """Version of the documented API (``info.version``)."""
    return str(tk.config.get(APIDOCS_SPEC_VERSION) or CKAN_VERSION)


def apidocs_token_header() -> str:
    """Header used to send the API token from the Swagger UI."""
    value = tk.config.get(APIDOCS_TOKEN_HEADER)
    if value:
        return str(value)

    return str(tk.config.get("apitoken_header_name") or DEFAULT_TOKEN_HEADER)


def apidocs_cache_ttl() -> int:
    """Number of seconds the generated spec is cached for. ``0`` disables it."""
    value = tk.config.get(APIDOCS_CACHE_TTL)
    if value is None or value == "":
        return DEFAULT_CACHE_TTL

    try:
        ttl = int(value)
    except (TypeError, ValueError):
        return DEFAULT_CACHE_TTL

    return max(ttl, 0)


def apidocs_require_login() -> bool:
    """Whether the documentation page is restricted to authenticated users."""
    return bool(tk.asbool(tk.config.get(APIDOCS_REQUIRE_LOGIN, False)))


def apidocs_sysadmin_only() -> bool:
    """Whether the documentation page is restricted to sysadmins."""
    return bool(tk.asbool(tk.config.get(APIDOCS_SYSADMIN_ONLY, False)))


def apidocs_allowed_users() -> list[str]:
    """Usernames the documentation is restricted to. Empty means "everyone"."""
    return _name_list(APIDOCS_ALLOWED_USERS)


def apidocs_access_restricted() -> bool:
    """Whether the configuration makes the documentation non-public."""
    return bool(
        apidocs_require_login()
        or apidocs_sysadmin_only()
        or apidocs_allowed_users()
    )


def apidocs_allows_user(
    name: str | None, sysadmin: bool = False
) -> bool:
    """Whether the user called ``name`` is allowed to see the documentation.

    Every user is allowed while no user based restriction is configured.
    ``ckanext.apidocs.sysadmin_only`` takes precedence over
    ``ckanext.apidocs.allowed_users``: only sysadmins are allowed while it is
    enabled. Names are compared case-insensitively, as CKAN treats usernames
    as case-insensitive.
    """
    if apidocs_sysadmin_only():
        return sysadmin

    allowed = {user.casefold() for user in apidocs_allowed_users()}
    if not allowed:
        return True

    return bool(name) and str(name).casefold() in allowed


def apidocs_included_extensions() -> list[str]:
    """Extensions whose actions are documented. Empty means "all"."""
    return _name_list(APIDOCS_INCLUDE_EXTENSIONS)


def apidocs_excluded_extensions() -> list[str]:
    """Extensions whose actions are never documented."""
    return _name_list(APIDOCS_EXCLUDE_EXTENSIONS)


def apidocs_ui_config() -> dict[str, Any]:
    """Options passed to the ``SwaggerUIBundle`` constructor."""
    validator_url = tk.config.get(APIDOCS_UI_VALIDATOR_URL)
    if validator_url is None:
        validator_url = DEFAULT_UI_VALIDATOR_URL

    doc_expansion = str(
        tk.config.get(APIDOCS_UI_DOC_EXPANSION) or DEFAULT_DOC_EXPANSION
    ).lower()
    if doc_expansion not in DOC_EXPANSION_VALUES:
        doc_expansion = DEFAULT_DOC_EXPANSION

    return {
        "docExpansion": doc_expansion,
        "deepLinking": bool(
            tk.asbool(tk.config.get(APIDOCS_UI_DEEP_LINKING, True))
        ),
        "filter": bool(tk.asbool(tk.config.get(APIDOCS_UI_FILTER, True))),
        "persistAuthorization": bool(
            tk.asbool(tk.config.get(APIDOCS_UI_PERSIST_AUTHORIZATION, True))
        ),
        "tryItOutEnabled": bool(
            tk.asbool(tk.config.get(APIDOCS_UI_TRY_IT_OUT, True))
        ),
        "validatorUrl": str(validator_url) or None,
    }


def _name_list(key: str) -> list[str]:
    raw = tk.config.get(key)
    if not raw:
        return []

    return [str(name).strip() for name in tk.aslist(raw) if str(name).strip()]
