"""Tests for ckanext.apidocs.logic.validators."""

from __future__ import annotations

import json
from copy import deepcopy

import pytest

import ckan.plugins.toolkit as tk

from ckanext.apidocs.logic.validators import (
    InvalidDefinition,
    apidocs_definition_valid,
    parse_definition,
)
from ckanext.apidocs.tests.data import MINIMAL_SPEC


# parsing


def test_a_mapping_is_accepted_as_is():
    assert parse_definition(deepcopy(MINIMAL_SPEC)) == MINIMAL_SPEC


def test_a_json_string_is_parsed():
    assert parse_definition(json.dumps(MINIMAL_SPEC)) == MINIMAL_SPEC


def test_a_yaml_string_is_parsed():
    yaml = pytest.importorskip("yaml")

    assert parse_definition(yaml.safe_dump(MINIMAL_SPEC)) == MINIMAL_SPEC


def test_an_empty_string_is_rejected():
    with pytest.raises(InvalidDefinition) as err:
        parse_definition("   ")

    assert "must be a JSON or YAML object" in str(err.value)


@pytest.mark.parametrize(
    "payload",
    ['{"openapi": ', "[1, 2, 3]", "{'not': 'json'"],
    ids=["json-syntax", "json-array", "python-repr"],
)
def test_a_document_that_is_not_a_mapping_is_rejected(payload):
    with pytest.raises(InvalidDefinition) as err:
        parse_definition(payload)

    assert err.value.errors


def test_unparseable_content_reports_both_formats():
    with pytest.raises(InvalidDefinition) as err:
        parse_definition("this: [is not\nvalid: json nor yaml")

    assert "Could not parse the document" in str(err.value)


# structure


@pytest.mark.parametrize("key", ["openapi", "info", "paths"])
def test_missing_required_keys_are_reported(key):
    document = deepcopy(MINIMAL_SPEC)
    del document[key]

    with pytest.raises(InvalidDefinition) as err:
        parse_definition(document)

    assert f"Missing required key: {key}" in str(err.value)


@pytest.mark.parametrize("version", ["2.0", "4.0", "swagger"])
def test_unsupported_openapi_versions_are_reported(version):
    with pytest.raises(InvalidDefinition) as err:
        parse_definition({**MINIMAL_SPEC, "openapi": version})

    assert "OpenAPI 3.x version" in str(err.value)


@pytest.mark.parametrize("version", ["3.0.0", "3.1.0"])
def test_openapi_3x_versions_are_accepted(version):
    document = {**MINIMAL_SPEC, "openapi": version}

    assert parse_definition(document)["openapi"] == version


def test_openapi_version_must_be_a_string():
    with pytest.raises(InvalidDefinition) as err:
        parse_definition({**MINIMAL_SPEC, "openapi": 3.0})

    assert "'openapi' must be a non-empty string" in str(err.value)


def test_a_malformed_info_object_is_reported():
    with pytest.raises(InvalidDefinition) as err:
        parse_definition({**MINIMAL_SPEC, "info": []})

    assert "'info' must be an object" in str(err.value)


@pytest.mark.parametrize("key", ["title", "version"])
def test_info_requires_a_title_and_a_version(key):
    info = {**MINIMAL_SPEC["info"]}
    del info[key]

    with pytest.raises(InvalidDefinition) as err:
        parse_definition({**MINIMAL_SPEC, "info": info})

    assert f"'info.{key}' must be a non-empty string" in str(err.value)


def test_a_malformed_paths_object_is_reported():
    with pytest.raises(InvalidDefinition) as err:
        parse_definition({**MINIMAL_SPEC, "paths": []})

    assert "'paths' must be an object" in str(err.value)


def test_paths_have_to_start_with_a_slash():
    with pytest.raises(InvalidDefinition) as err:
        parse_definition({**MINIMAL_SPEC, "paths": {"package_show": {}}})

    assert "must start with '/'" in str(err.value)


def test_paths_allow_extensions():
    document = {**MINIMAL_SPEC, "paths": {"x-internal": {}}}

    assert parse_definition(document) == document


# validator


def _validate(value):
    """Run the validator the way navl does and return the parsed value."""
    key = ("definition",)
    data = {key: value}

    apidocs_definition_valid(key, data, {key: []}, {})

    return data[key]


def test_the_validator_replaces_the_value_with_the_parsed_document():
    assert _validate(json.dumps(MINIMAL_SPEC)) == MINIMAL_SPEC


def test_the_validator_raises_invalid_for_a_broken_document():
    with pytest.raises(tk.Invalid):
        _validate("{not json")
