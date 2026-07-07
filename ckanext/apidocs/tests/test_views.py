"""Tests for views.py."""

import pytest

import ckan.plugins.toolkit as tk


@pytest.mark.ckan_config("ckan.plugins", "apidocs")
@pytest.mark.usefixtures("with_plugins")
def test_apidocs_index(app):
    url = tk.h.url_for("apidocs.index")
    resp = app.get(url)
    assert resp.status_code == 200
    body = resp.body.decode('utf-8') if isinstance(resp.body, (bytes, bytearray)) else resp.body
    assert "Click" in body or "Authorize" in body


@pytest.mark.ckan_config("ckan.plugins", "apidocs")
@pytest.mark.usefixtures("with_plugins")
def test_openapi_yaml_endpoint(app):
    url = tk.h.url_for("apidocs.openapi_yaml")
    resp = app.get(url)
    assert resp.status_code == 200
    body = resp.body.decode('utf-8') if isinstance(resp.body, (bytes, bytearray)) else resp.body
    assert "openapi" in body
    assert "/api/3/action/package_show" in body
    assert "Authorization" in body


@pytest.mark.ckan_config("ckan.plugins", "apidocs")
@pytest.mark.usefixtures("with_plugins")
def test_openapi_json_endpoint(app):
    url = tk.h.url_for("apidocs.openapi_json")
    resp = app.get(url)
    assert resp.status_code == 200
    body = resp.body.decode('utf-8') if isinstance(resp.body, (bytes, bytearray)) else resp.body
    assert '"openapi": "3.0.0"' in body
    assert '"/api/3/action/package_show"' in body
    assert "Authorization" in body
