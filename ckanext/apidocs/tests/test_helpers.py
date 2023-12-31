"""Tests for helpers.py."""

import ckanext.apidocs.helpers as helpers


def test_apidocs_hello():
    assert helpers.apidocs_hello() == "Hello, apidocs!"
