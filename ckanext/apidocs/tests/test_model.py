"""Tests for ckanext.apidocs.model."""

from __future__ import annotations

import pytest

from ckanext.apidocs.model import ApidocsSchema, ApidocsSchemaState
from ckanext.apidocs.tests.data import (
    MINIMAL_SPEC,
    UNSORTED_SPEC,
    UNSORTED_SPEC_KEYS,
    UNSORTED_SPEC_PATHS,
)


pytestmark = [
    pytest.mark.ckan_config("ckan.plugins", "apidocs"),
    pytest.mark.usefixtures("with_plugins", "clean_db"),
]


def test_get_returns_nothing_when_no_document_is_stored():
    assert ApidocsSchema.get() is None


def test_set_definition_creates_the_row():
    row = ApidocsSchema.set_definition(dict(MINIMAL_SPEC))

    stored = ApidocsSchema.get()

    assert stored is not None
    assert stored.name == "openapi"
    assert stored.definition == MINIMAL_SPEC
    assert stored.updated is not None
    assert row.name == "openapi"


def test_set_definition_replaces_the_document():
    ApidocsSchema.set_definition(dict(MINIMAL_SPEC))

    updated = {**MINIMAL_SPEC, "info": {"title": "New", "version": "2.0"}}
    ApidocsSchema.set_definition(updated)

    stored = ApidocsSchema.get()

    assert stored is not None
    assert stored.definition == updated


def test_fingerprint_is_empty_without_a_document():
    assert ApidocsSchemaState.fingerprint() == (0, None)


def test_fingerprint_changes_on_every_write():
    ApidocsSchema.set_definition(dict(MINIMAL_SPEC))
    first = ApidocsSchemaState.fingerprint()

    ApidocsSchema.set_definition(dict(MINIMAL_SPEC))
    second = ApidocsSchemaState.fingerprint()

    assert first[0] == 1
    assert second[0] == 2
    assert first[1] is not None
    assert second[1] is not None
    assert second[1] >= first[1]


def test_delete_removes_the_document_and_bumps_the_version():
    row = ApidocsSchema.set_definition(dict(MINIMAL_SPEC))

    row.delete()

    assert ApidocsSchema.get() is None
    assert ApidocsSchemaState.fingerprint()[0] == 2


def test_as_dict_serializes_the_updated_timestamp():
    row = ApidocsSchema.set_definition(dict(MINIMAL_SPEC))

    payload = row.as_dict()

    assert payload["name"] == "openapi"
    assert payload["definition"] == MINIMAL_SPEC
    assert isinstance(payload["updated"], str)


# canonical order


def test_set_definition_stores_the_keys_alphabetically():
    row = ApidocsSchema.set_definition(dict(UNSORTED_SPEC))

    assert list(row.definition) == UNSORTED_SPEC_KEYS
    assert list(row.definition["paths"]) == UNSORTED_SPEC_PATHS


def test_the_canonical_order_is_restored_when_the_row_is_read():
    ApidocsSchema.set_definition(dict(UNSORTED_SPEC))

    stored = ApidocsSchema.get()

    assert stored is not None
    assert stored.canonical_definition == UNSORTED_SPEC
    assert list(stored.canonical_definition) == UNSORTED_SPEC_KEYS
    assert list(stored.canonical_definition["paths"]) == UNSORTED_SPEC_PATHS


def test_as_dict_returns_the_canonical_definition():
    ApidocsSchema.set_definition(dict(UNSORTED_SPEC))

    stored = ApidocsSchema.get()

    assert stored is not None
    assert list(stored.as_dict()["definition"]) == UNSORTED_SPEC_KEYS
