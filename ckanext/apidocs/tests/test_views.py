"""Tests for views.py."""

import pytest

import ckanext.apidocs.validators as validators


import ckan.plugins.toolkit as tk


@pytest.mark.ckan_config("ckan.plugins", "apidocs")
@pytest.mark.usefixtures("with_plugins")
def test_apidocs_blueprint(app, reset_db):
    resp = app.get(tk.h.url_for("apidocs.page"))
    assert resp.status_code == 200
    assert resp.body == "Hello, apidocs!"
