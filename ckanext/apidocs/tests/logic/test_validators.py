"""Tests for validators.py."""

import pytest

import ckan.plugins.toolkit as tk

from ckanext.apidocs.logic import validators


def test_apidocs_reauired_with_valid_value():
    assert validators.apidocs_required("value") == "value"


def test_apidocs_reauired_with_invalid_value():
    with pytest.raises(tk.Invalid):
        validators.apidocs_required(None)
