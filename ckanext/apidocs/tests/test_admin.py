"""Tests for the sysadmin page managing the stored OpenAPI document."""

from __future__ import annotations

import html
import json

import pytest
import yaml

import ckan.plugins.toolkit as tk
from ckan.tests import factories

from ckanext.apidocs.model import ApidocsSchema
from ckanext.apidocs.tests.data import (
    MINIMAL_SPEC,
    UNSORTED_SPEC,
    UNSORTED_SPEC_KEYS,
    UNSORTED_SPEC_PATHS,
)


STATUS_OK = 200
STATUS_REDIRECT = 302
STATUS_BAD_REQUEST = 400
STATUS_FORBIDDEN = 403

INDEX_URL = "/ckan-admin/apidocs/"
SAVE_URL = "/ckan-admin/apidocs/save"
RESET_URL = "/ckan-admin/apidocs/reset"
FORMAT_URL = "/ckan-admin/apidocs/format"
GENERATED_URL = "/ckan-admin/apidocs/generated"

pytestmark = [
    pytest.mark.ckan_config("ckan.plugins", "apidocs"),
    pytest.mark.usefixtures("with_plugins", "clean_db"),
]


def _sysadmin_headers() -> dict[str, str]:
    return {"Authorization": factories.SysadminWithToken()["token"]}


class TestAccess:
    @pytest.mark.usefixtures("with_request_context")
    def test_the_endpoints_are_registered(self):
        assert tk.url_for("apidocs_admin.index") == INDEX_URL
        assert tk.url_for("apidocs_admin.save") == SAVE_URL
        assert tk.url_for("apidocs_admin.reset") == RESET_URL
        assert tk.url_for("apidocs_admin.format") == FORMAT_URL
        assert tk.url_for("apidocs_admin.generated") == GENERATED_URL

    def test_a_sysadmin_sees_the_page(self, app):
        resp = app.get(INDEX_URL, headers=_sysadmin_headers())

        assert resp.status_code == STATUS_OK
        assert 'name="definition"' in resp.body

    def test_anonymous_visitors_are_forbidden(self, app):
        app.get(INDEX_URL, status=STATUS_FORBIDDEN)

    def test_regular_users_are_forbidden(self, app):
        headers = {"Authorization": factories.UserWithToken()["token"]}

        app.get(INDEX_URL, headers=headers, status=STATUS_FORBIDDEN)
        app.post(
            SAVE_URL,
            headers=headers,
            data={"definition": json.dumps(MINIMAL_SPEC)},
            status=STATUS_FORBIDDEN,
        )

    def test_the_helper_endpoints_require_a_sysadmin(self, app):
        app.get(GENERATED_URL, status=STATUS_FORBIDDEN)
        app.post(
            FORMAT_URL,
            data={"definition": json.dumps(MINIMAL_SPEC)},
            status=STATUS_FORBIDDEN,
        )
        app.post(RESET_URL, status=STATUS_FORBIDDEN)

    def test_the_link_is_added_to_the_admin_navigation(self, app):
        resp = app.get(INDEX_URL, headers=_sysadmin_headers())

        assert f'href="{INDEX_URL}"' in resp.body
        assert "API documentation" in resp.body

    def test_the_editor_is_wired_to_the_helper_endpoints(self, app):
        resp = app.get(INDEX_URL, headers=_sysadmin_headers())

        assert 'data-module="apidocs-schema-editor"' in resp.body
        assert f'data-module-format-url="{FORMAT_URL}"' in resp.body
        assert f'data-module-generated-url="{GENERATED_URL}"' in resp.body
        assert "-apidocs-admin.js" in resp.body

    def test_the_reset_link_sits_before_the_save_button(self, app):
        ApidocsSchema.set_definition(dict(MINIMAL_SPEC))

        resp = app.get(INDEX_URL, headers=_sysadmin_headers())

        # From 576px up `.form-actions` is a plain row (as in core's
        # group/member_new.html), so the DOM order is the visual order: the
        # destructive link, which renders itself through `confirm-action`
        # using its href, ends up on the same line, before the save button.
        actions = resp.body.split('<div class="form-actions">')[1].split(
            "</div>"
        )[0]

        assert f'href="{RESET_URL}"' in actions
        assert 'data-module="confirm-action"' in actions
        assert 'type="submit"' in actions
        assert actions.index(RESET_URL) < actions.index('type="submit"')

        # a single actions row, the reset link is not a form of its own
        assert resp.body.count('<div class="form-actions">') == 1
        assert 'id="apidocs-schema-reset"' not in resp.body


class TestIndex:
    def test_the_generated_document_is_shown_by_default(self, app):
        resp = app.get(INDEX_URL, headers=_sysadmin_headers())

        # the generated document is prefilled so it can be edited and saved
        # (the textarea value is HTML escaped, hence no quotes here)
        assert "package_show" in resp.body
        assert "generated from the registered actions" in resp.body
        assert f'href="{RESET_URL}"' not in resp.body

    def test_the_stored_document_is_shown(self, app):
        ApidocsSchema.set_definition(dict(MINIMAL_SPEC))

        resp = app.get(INDEX_URL, headers=_sysadmin_headers())

        assert "Custom API" in resp.body
        assert "served from the schema stored" in resp.body
        assert f'href="{RESET_URL}"' in resp.body

    def test_the_stored_document_is_shown_in_alphabetical_order(self, app):
        ApidocsSchema.set_definition(dict(UNSORTED_SPEC))

        resp = app.get(INDEX_URL, headers=_sysadmin_headers())

        # the textarea value is HTML escaped, so unescape before comparing
        body = html.unescape(resp.body)

        assert body.index('"info"') < body.index('"openapi"')
        assert body.index('"/alpha"') < body.index('"/zulu"')


class TestSave:
    def test_a_json_document_is_stored(self, app):
        resp = app.post(
            SAVE_URL,
            headers=_sysadmin_headers(),
            data={"definition": json.dumps(MINIMAL_SPEC)},
            follow_redirects=False,
        )

        assert resp.status_code == STATUS_REDIRECT

        stored = ApidocsSchema.get()

        assert stored is not None
        assert stored.definition == MINIMAL_SPEC

    def test_a_yaml_document_is_stored(self, app):
        resp = app.post(
            SAVE_URL,
            headers=_sysadmin_headers(),
            data={"definition": yaml.safe_dump(MINIMAL_SPEC)},
            follow_redirects=False,
        )

        assert resp.status_code == STATUS_REDIRECT

        stored = ApidocsSchema.get()

        assert stored is not None
        assert stored.definition == MINIMAL_SPEC

    def test_an_invalid_document_is_reported(self, app):
        resp = app.post(
            SAVE_URL,
            headers=_sysadmin_headers(),
            data={"definition": "{not json"},
        )

        assert resp.status_code == STATUS_OK
        assert "Could not parse the document" in resp.body
        assert "{not json" in resp.body  # the editor keeps the posted content
        assert ApidocsSchema.get() is None

    def test_a_document_without_the_required_keys_is_reported(self, app):
        resp = app.post(
            SAVE_URL,
            headers=_sysadmin_headers(),
            data={"definition": json.dumps({"openapi": "3.0.0"})},
        )

        assert resp.status_code == STATUS_OK
        assert "Missing required key: info" in resp.body
        assert ApidocsSchema.get() is None

    def test_saving_replaces_the_previous_document(self, app):
        headers = _sysadmin_headers()
        app.post(
            SAVE_URL,
            headers=headers,
            data={"definition": json.dumps(MINIMAL_SPEC)},
        )

        updated = {**MINIMAL_SPEC, "info": {"title": "Another", "version": "2.0"}}
        app.post(SAVE_URL, headers=headers, data={"definition": json.dumps(updated)})

        stored = ApidocsSchema.get()

        assert stored is not None
        assert stored.definition == updated


class TestReset:
    def test_the_stored_document_is_removed(self, app):
        ApidocsSchema.set_definition(dict(MINIMAL_SPEC))

        resp = app.post(
            RESET_URL, headers=_sysadmin_headers(), follow_redirects=False
        )

        assert resp.status_code == STATUS_REDIRECT
        assert ApidocsSchema.get() is None

    def test_resetting_without_a_stored_document_is_reported(self, app):
        resp = app.post(RESET_URL, headers=_sysadmin_headers())

        assert resp.status_code == STATUS_OK
        assert "no stored API documentation schema" in resp.body


class TestFormat:
    def test_yaml_is_converted_to_json(self, app):
        resp = app.post(
            FORMAT_URL,
            headers=_sysadmin_headers(),
            data={"definition": yaml.safe_dump(MINIMAL_SPEC)},
        )

        assert resp.status_code == STATUS_OK
        assert json.loads(resp.body) == MINIMAL_SPEC

    def test_json_is_pretty_printed(self, app):
        resp = app.post(
            FORMAT_URL,
            headers=_sysadmin_headers(),
            data={"definition": json.dumps(MINIMAL_SPEC)},
        )

        assert resp.status_code == STATUS_OK
        assert resp.body.startswith('{\n  "')
        assert json.loads(resp.body) == MINIMAL_SPEC

    def test_the_document_is_returned_in_alphabetical_order(self, app):
        resp = app.post(
            FORMAT_URL,
            headers=_sysadmin_headers(),
            data={"definition": json.dumps(UNSORTED_SPEC)},
        )

        assert resp.status_code == STATUS_OK

        payload = json.loads(resp.body)

        assert list(payload) == UNSORTED_SPEC_KEYS
        assert list(payload["paths"]) == UNSORTED_SPEC_PATHS

    def test_a_broken_document_is_reported(self, app):
        resp = app.post(
            FORMAT_URL,
            headers=_sysadmin_headers(),
            data={"definition": "{not json"},
        )

        assert resp.status_code == STATUS_BAD_REQUEST
        assert json.loads(resp.body)["errors"]

    def test_a_document_without_the_required_keys_is_reported(self, app):
        resp = app.post(
            FORMAT_URL,
            headers=_sysadmin_headers(),
            data={"definition": json.dumps({"paths": {}})},
        )

        assert resp.status_code == STATUS_BAD_REQUEST
        assert "Missing required key: openapi" in resp.body


class TestGenerated:
    def test_the_generated_document_is_returned(self, app):
        ApidocsSchema.set_definition(dict(MINIMAL_SPEC))

        resp = app.get(GENERATED_URL, headers=_sysadmin_headers())

        assert resp.status_code == STATUS_OK

        payload = json.loads(resp.body)

        assert "/package_show" in payload["paths"]
        assert "/custom_action" not in payload["paths"]
