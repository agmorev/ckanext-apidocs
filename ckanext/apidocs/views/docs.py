"""Web views of the API documentation.

The blueprint serves the Swagger UI page and the OpenAPI documents at
``/api/docs/``. The document is the one stored by a sysadmin when there is
one, otherwise it is generated from the registered actions.
"""

from __future__ import annotations

from flask import Blueprint
from flask.wrappers import Response

from ckan.plugins import toolkit as tk

from ckanext.apidocs import config, helpers


bp = Blueprint("apidocs", __name__, url_prefix="/api/docs/")


@bp.before_request
def _restrict_access():
    """Optionally restrict the documentation to authenticated users.

    ``ckanext.apidocs.require_login`` accepts any signed in user while
    ``ckanext.apidocs.sysadmin_only`` and ``ckanext.apidocs.allowed_users``
    narrow the access down to sysadmins or to the listed usernames. Both of
    them require authentication on their own.
    """
    if not config.apidocs_access_restricted():
        return None

    if not tk.current_user.is_authenticated:
        if tk.request.endpoint == "apidocs.index":
            return tk.redirect_to("user.login")

        return tk.abort(
            403, "Authentication is required to access the API documentation"
        )

    if not config.apidocs_allows_user(
        tk.current_user.name, bool(tk.current_user.sysadmin)
    ):
        return tk.abort(
            403, "You are not allowed to access the API documentation"
        )

    return None


def index() -> str:
    """Render the Swagger UI page."""
    spec = helpers.get_openapi_spec()

    return tk.render(
        "apidocs/index.html",
        extra_vars={
            "title": config.apidocs_title(),
            "apidocs_config": {
                "specUrl": tk.url_for("apidocs.ckanapi_json"),
                "ui": config.apidocs_ui_config(),
                "badges": helpers.collect_badges(spec),
            },
        },
    )


def ckanapi_json() -> Response:
    """The generated OpenAPI document, serialized as JSON."""
    return _spec_response(
        helpers.dumps_openapi_json(helpers.get_openapi_spec()),
        "application/json",
    )


def ckanapi_yaml() -> Response:
    """The generated OpenAPI document, serialized as YAML."""
    return _spec_response(
        helpers.dump_openapi_yaml(helpers.get_openapi_spec()),
        "application/x-yaml",
    )


def _spec_response(payload: str, mimetype: str) -> Response:
    """Return the serialized specification with an ``ETag``.

    The ``Cache-Control`` header of the response is owned by CKAN's cache
    middleware and is configured with the ``ckan.cache_enabled`` and
    ``ckan.cache_expires`` settings.
    """
    etag = helpers.spec_etag(payload)

    if etag in tk.request.if_none_match:
        response = Response(status=304)
    else:
        response = Response(payload, mimetype=mimetype)

    response.headers["ETag"] = f'"{etag}"'

    return response


bp.add_url_rule("/", endpoint="index", view_func=index)

bp.add_url_rule(
    "/ckanapi.json", endpoint="ckanapi_json", view_func=ckanapi_json
)
bp.add_url_rule(
    "/ckanapi.yaml", endpoint="ckanapi_yaml", view_func=ckanapi_yaml
)

# Aliases following the OpenAPI naming convention
bp.add_url_rule(
    "/openapi.json", endpoint="openapi_json", view_func=ckanapi_json
)
bp.add_url_rule(
    "/openapi.yaml", endpoint="openapi_yaml", view_func=ckanapi_yaml
)
