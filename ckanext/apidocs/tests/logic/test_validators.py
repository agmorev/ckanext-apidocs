"""Tests for validators.py."""

import pytest

import ckan.plugins.toolkit as tk

from ckanext.example.logic import validators


def test_example_reauired_with_valid_value():
    assert validators.example_required("value") == "value"


def test_example_reauired_with_invalid_value():
    with pytest.raises(tk.Invalid):
        validators.example_required(None)
