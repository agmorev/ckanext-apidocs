"""Tests for ckanext.apidocs.views."""

from __future__ import annotations

import json

import pytest

from ckan.plugins import toolkit as tk
from ckan.tests import factories

from ckanext.apidocs import helpers
from ckanext.apidocs.model import ApidocsSchema
from ckanext.apidocs.tests.data import MINIMAL_SPEC


INDEX_URL = "/api/docs/"
JSON_URL = "/api/docs/ckanapi.json"
YAML_URL = "/api/docs/ckanapi.yaml"


def _auth_headers(user):
    """Headers that authenticate the request as ``user``."""
    return {"Authorization": user["token"]}


@pytest.mark.ckan_config("ckan.plugins", "apidocs")
@pytest.mark.usefixtures("with_plugins")
def test_index_renders_swagger_ui(app):
    response = app.get(INDEX_URL)

    assert response.status_code == 200
    assert 'id="swagger-ui"' in response.body
    assert 'data-module="apidocs-swagger"' in response.body


@pytest.mark.ckan_config("ckan.plugins", "apidocs")
@pytest.mark.usefixtures("with_plugins")
def test_index_embeds_the_page_configuration(app):
    response = app.get(INDEX_URL)

    assert '"specUrl": "/api/docs/ckanapi.json"' in response.body
    assert '"badges"' in response.body
    assert '"docExpansion"' in response.body


@pytest.mark.ckan_config("ckan.plugins", "apidocs")
@pytest.mark.usefixtures("with_plugins")
def test_index_loads_the_extension_assets(app):
    response = app.get(INDEX_URL)

    assert "-apidocs.css" in response.body
    assert "-apidocs.js" in response.body


@pytest.mark.ckan_config("ckan.plugins", "apidocs")
@pytest.mark.usefixtures("with_plugins")
def test_index_keeps_the_theme_assets(app):
    # The scripts block of the page must keep the assets registered by
    # page.html (base/main and base/ckan), i.e. it must call super().
    response = app.get(INDEX_URL)

    assert "_main.js" in response.body
    assert "_ckan.js" in response.body


@pytest.mark.ckan_config("ckan.plugins", "apidocs")
@pytest.mark.usefixtures("with_plugins", "with_request_context")
def test_endpoints_are_registered(app):
    assert tk.url_for("apidocs.index") == INDEX_URL
    assert tk.url_for("apidocs.ckanapi_json") == JSON_URL
    assert tk.url_for("apidocs.ckanapi_yaml") == YAML_URL
    assert tk.url_for("apidocs.openapi_json") == "/api/docs/openapi.json"
    assert tk.url_for("apidocs.openapi_yaml") == "/api/docs/openapi.yaml"


@pytest.mark.ckan_config("ckan.plugins", "apidocs")
@pytest.mark.usefixtures("with_plugins")
@pytest.mark.parametrize(
    "url", [JSON_URL, "/api/docs/openapi.json"], ids=["json", "json-alias"]
)
def test_ckanapi_json(app, url):
    response = app.get(url)

    assert response.status_code == 200
    assert response.headers["Content-Type"].startswith("application/json")

    payload = json.loads(response.body)

    assert payload["openapi"] == "3.0.0"
    assert "/package_show" in payload["paths"]
    assert (
        payload["components"]["securitySchemes"]["ApiKeyAuth"]["name"]
        == "Authorization"
    )


@pytest.mark.ckan_config("ckan.plugins", "apidocs")
@pytest.mark.usefixtures("with_plugins")
@pytest.mark.parametrize(
    "url", [YAML_URL, "/api/docs/openapi.yaml"], ids=["yaml", "yaml-alias"]
)
def test_ckanapi_yaml(app, url):
    yaml = pytest.importorskip("yaml")

    response = app.get(url)

    assert response.status_code == 200

    payload = yaml.safe_load(response.body)

    assert payload["openapi"] == "3.0.0"
    assert "/package_show" in payload["paths"]


@pytest.mark.ckan_config("ckan.plugins", "apidocs")
@pytest.mark.usefixtures("with_plugins", "clean_db")
def test_ckanapi_json_serves_the_stored_document(app):
    ApidocsSchema.set_definition(dict(MINIMAL_SPEC))

    payload = json.loads(app.get(JSON_URL).body)

    assert "/custom_action" in payload["paths"]
    assert "/package_show" not in payload["paths"]


@pytest.mark.ckan_config("ckan.plugins", "apidocs")
@pytest.mark.usefixtures("with_plugins", "clean_db")
def test_ckanapi_yaml_serves_the_stored_document(app):
    yaml = pytest.importorskip("yaml")

    ApidocsSchema.set_definition(dict(MINIMAL_SPEC))

    payload = yaml.safe_load(app.get(YAML_URL).body)

    assert "/custom_action" in payload["paths"]
    assert "/package_show" not in payload["paths"]


@pytest.mark.ckan_config("ckan.plugins", "apidocs")
@pytest.mark.usefixtures("with_plugins", "clean_db")
def test_the_etag_changes_when_a_document_is_stored(app):
    default = app.get(JSON_URL).headers["ETag"]

    ApidocsSchema.set_definition(dict(MINIMAL_SPEC))

    assert app.get(JSON_URL).headers["ETag"] != default


@pytest.mark.ckan_config("ckan.plugins", "apidocs")
@pytest.mark.usefixtures("with_plugins")
def test_spec_endpoint_supports_conditional_requests(app):
    first = app.get(JSON_URL)
    etag = first.headers["ETag"]

    assert etag

    second = app.get(JSON_URL, headers={"If-None-Match": etag})

    assert second.status_code == 304
    assert second.body == ""


@pytest.mark.ckan_config("ckan.plugins", "apidocs")
@pytest.mark.usefixtures("with_plugins")
def test_spec_endpoint_sends_an_etag(app):
    response = app.get(JSON_URL)

    etag = response.headers["ETag"]

    assert etag.startswith('"')
    assert etag == f'"{helpers.spec_etag(response.body)}"'


@pytest.mark.ckan_config("ckan.plugins", "apidocs")
@pytest.mark.usefixtures("with_plugins")
def test_spec_endpoint_etag_changes_with_the_document(app):
    default = app.get(JSON_URL).headers["ETag"]

    with pytest.MonkeyPatch.context() as patch:
        patch.setitem(tk.config, "ckanext.apidocs.title", "Another title")
        helpers.invalidate_cache()
        changed = app.get(JSON_URL).headers["ETag"]

    assert default != changed


@pytest.mark.ckan_config("ckan.plugins", "apidocs")
@pytest.mark.ckan_config("ckanext.apidocs.enable_api_methods", "GET")
@pytest.mark.usefixtures("with_plugins")
def test_spec_endpoint_respects_enabled_methods(app):
    payload = json.loads(app.get(JSON_URL).body)

    assert "/package_show" in payload["paths"]
    assert "/package_create" not in payload["paths"]


@pytest.mark.ckan_config("ckan.plugins", "apidocs")
@pytest.mark.ckan_config("ckanext.apidocs.require_login", True)
@pytest.mark.usefixtures("with_plugins")
def test_spec_endpoint_requires_login_when_configured(app):
    response = app.get(JSON_URL)

    assert response.status_code == 403


@pytest.mark.ckan_config("ckan.plugins", "apidocs")
@pytest.mark.ckan_config("ckanext.apidocs.require_login", True)
@pytest.mark.usefixtures("with_plugins")
def test_index_redirects_to_login_when_configured(app):
    response = app.get(INDEX_URL, follow_redirects=False)

    assert response.status_code == 302
    assert "/user/login" in response.headers["Location"]


@pytest.mark.ckan_config("ckan.plugins", "apidocs")
@pytest.mark.ckan_config("ckanext.apidocs.require_login", True)
@pytest.mark.usefixtures("with_plugins", "clean_db")
def test_any_authenticated_user_is_allowed_without_the_allowlist(app):
    user = factories.UserWithToken()

    assert app.get(JSON_URL, headers=_auth_headers(user)).status_code == 200


@pytest.mark.ckan_config("ckan.plugins", "apidocs")
@pytest.mark.ckan_config("ckanext.apidocs.allowed_users", "editor")
@pytest.mark.usefixtures("with_plugins")
def test_allowed_users_restrict_anonymous_access(app):
    # The allowlist requires authentication on its own, even though
    # `require_login` is left disabled.
    assert app.get(JSON_URL).status_code == 403


@pytest.mark.ckan_config("ckan.plugins", "apidocs")
@pytest.mark.ckan_config("ckanext.apidocs.allowed_users", "editor")
@pytest.mark.usefixtures("with_plugins")
def test_allowed_users_redirect_anonymous_visitors_to_login(app):
    response = app.get(INDEX_URL, follow_redirects=False)

    assert response.status_code == 302
    assert "/user/login" in response.headers["Location"]


@pytest.mark.ckan_config("ckan.plugins", "apidocs")
@pytest.mark.ckan_config("ckanext.apidocs.allowed_users", "editor")
@pytest.mark.usefixtures("with_plugins", "clean_db")
def test_allowed_users_grant_access_to_the_listed_user(app):
    user = factories.UserWithToken(name="editor")

    assert app.get(JSON_URL, headers=_auth_headers(user)).status_code == 200
    assert app.get(INDEX_URL, headers=_auth_headers(user)).status_code == 200


@pytest.mark.ckan_config("ckan.plugins", "apidocs")
@pytest.mark.ckan_config("ckanext.apidocs.allowed_users", "editor")
@pytest.mark.usefixtures("with_plugins", "clean_db")
def test_allowed_users_deny_other_users(app):
    user = factories.UserWithToken(name="other")

    assert app.get(JSON_URL, headers=_auth_headers(user)).status_code == 403
    assert app.get(INDEX_URL, headers=_auth_headers(user)).status_code == 403


@pytest.mark.ckan_config("ckan.plugins", "apidocs")
@pytest.mark.ckan_config("ckanext.apidocs.allowed_users", "Editor")
@pytest.mark.usefixtures("with_plugins", "clean_db")
def test_allowed_users_are_matched_case_insensitively(app):
    user = factories.UserWithToken(name="editor")

    assert app.get(JSON_URL, headers=_auth_headers(user)).status_code == 200


@pytest.mark.ckan_config("ckan.plugins", "apidocs")
@pytest.mark.ckan_config("ckanext.apidocs.allowed_users", "editor")
@pytest.mark.ckan_config("ckanext.apidocs.require_login", True)
@pytest.mark.usefixtures("with_plugins", "clean_db")
def test_allowed_users_narrow_down_require_login(app):
    editor = factories.UserWithToken(name="editor")
    other = factories.UserWithToken(name="other")

    assert app.get(JSON_URL, headers=_auth_headers(editor)).status_code == 200
    assert app.get(JSON_URL, headers=_auth_headers(other)).status_code == 403


@pytest.mark.ckan_config("ckan.plugins", "apidocs")
@pytest.mark.ckan_config("ckanext.apidocs.sysadmin_only", True)
@pytest.mark.usefixtures("with_plugins")
def test_sysadmin_only_restricts_anonymous_access(app):
    assert app.get(JSON_URL).status_code == 403


@pytest.mark.ckan_config("ckan.plugins", "apidocs")
@pytest.mark.ckan_config("ckanext.apidocs.sysadmin_only", True)
@pytest.mark.usefixtures("with_plugins")
def test_sysadmin_only_redirects_anonymous_visitors_to_login(app):
    response = app.get(INDEX_URL, follow_redirects=False)

    assert response.status_code == 302
    assert "/user/login" in response.headers["Location"]


@pytest.mark.ckan_config("ckan.plugins", "apidocs")
@pytest.mark.ckan_config("ckanext.apidocs.sysadmin_only", True)
@pytest.mark.usefixtures("with_plugins", "clean_db")
def test_sysadmin_only_grant_access_to_sysadmins(app):
    user = factories.UserWithToken(sysadmin=True)

    assert app.get(JSON_URL, headers=_auth_headers(user)).status_code == 200
    assert app.get(INDEX_URL, headers=_auth_headers(user)).status_code == 200


@pytest.mark.ckan_config("ckan.plugins", "apidocs")
@pytest.mark.ckan_config("ckanext.apidocs.sysadmin_only", True)
@pytest.mark.usefixtures("with_plugins", "clean_db")
def test_sysadmin_only_deny_other_users(app):
    user = factories.UserWithToken()

    assert app.get(JSON_URL, headers=_auth_headers(user)).status_code == 403
    assert app.get(INDEX_URL, headers=_auth_headers(user)).status_code == 403


@pytest.mark.ckan_config("ckan.plugins", "apidocs")
@pytest.mark.ckan_config("ckanext.apidocs.sysadmin_only", True)
@pytest.mark.ckan_config("ckanext.apidocs.allowed_users", "editor")
@pytest.mark.usefixtures("with_plugins", "clean_db")
def test_sysadmin_only_takes_precedence_over_the_allowlist(app):
    editor = factories.UserWithToken(name="editor")
    sysadmin = factories.UserWithToken(sysadmin=True)

    assert app.get(JSON_URL, headers=_auth_headers(sysadmin)).status_code == 200
    assert app.get(JSON_URL, headers=_auth_headers(editor)).status_code == 403
