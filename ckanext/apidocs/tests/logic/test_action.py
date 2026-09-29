"""Tests for ckanext.apidocs.logic.action."""

from __future__ import annotations

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


pytestmark = [
    pytest.mark.ckan_config("ckan.plugins", "apidocs"),
    pytest.mark.usefixtures("with_plugins", "clean_db"),
]


def _sysadmin_context() -> dict[str, str]:
    return {"user": factories.Sysadmin()["name"]}


class TestUpdate:
    def test_a_json_string_is_stored(self):
        result = tk.get_action("apidocs_schema_update")(
            _sysadmin_context(), {"definition": json.dumps(MINIMAL_SPEC)}
        )

        assert result["definition"] == MINIMAL_SPEC
        assert result["name"] == "openapi"
        assert result["updated"]

        stored = ApidocsSchema.get()

        assert stored is not None
        assert stored.definition == MINIMAL_SPEC

    def test_a_yaml_string_is_stored_as_json(self):
        tk.get_action("apidocs_schema_update")(
            _sysadmin_context(), {"definition": yaml.safe_dump(MINIMAL_SPEC)}
        )

        stored = ApidocsSchema.get()

        assert stored is not None
        assert stored.definition == MINIMAL_SPEC

    def test_a_mapping_is_stored(self):
        tk.get_action("apidocs_schema_update")(
            _sysadmin_context(), {"definition": dict(MINIMAL_SPEC)}
        )

        stored = ApidocsSchema.get()

        assert stored is not None
        assert stored.definition == MINIMAL_SPEC

    def test_saving_twice_replaces_the_document(self):
        action = tk.get_action("apidocs_schema_update")
        action(_sysadmin_context(), {"definition": dict(MINIMAL_SPEC)})

        updated = {**MINIMAL_SPEC, "info": {"title": "New", "version": "2.0"}}
        action(_sysadmin_context(), {"definition": updated})

        stored = ApidocsSchema.get()

        assert stored is not None
        assert stored.definition == updated

    def test_a_missing_definition_is_rejected(self):
        with pytest.raises(tk.ValidationError):
            tk.get_action("apidocs_schema_update")(_sysadmin_context(), {})

    def test_the_document_is_stored_in_alphabetical_order(self):
        result = tk.get_action("apidocs_schema_update")(
            _sysadmin_context(), {"definition": dict(UNSORTED_SPEC)}
        )

        assert list(result["definition"]) == UNSORTED_SPEC_KEYS
        assert list(result["definition"]["paths"]) == UNSORTED_SPEC_PATHS

    def test_an_invalid_document_is_rejected(self):
        with pytest.raises(tk.ValidationError) as err:
            tk.get_action("apidocs_schema_update")(
                _sysadmin_context(), {"definition": "{not json"}
            )

        assert "definition" in err.value.error_dict
        assert ApidocsSchema.get() is None


class TestShow:
    def test_an_empty_dict_is_returned_when_nothing_is_stored(self):
        assert (
            tk.get_action("apidocs_schema_show")(_sysadmin_context(), {}) == {}
        )

    def test_the_stored_document_is_returned(self):
        tk.get_action("apidocs_schema_update")(
            _sysadmin_context(), {"definition": dict(MINIMAL_SPEC)}
        )

        result = tk.get_action("apidocs_schema_show")(_sysadmin_context(), {})

        assert result["definition"] == MINIMAL_SPEC
        assert result["name"] == "openapi"

    def test_the_stored_document_is_returned_in_alphabetical_order(self):
        tk.get_action("apidocs_schema_update")(
            _sysadmin_context(), {"definition": dict(UNSORTED_SPEC)}
        )

        result = tk.get_action("apidocs_schema_show")(_sysadmin_context(), {})

        assert list(result["definition"]) == UNSORTED_SPEC_KEYS
        assert list(result["definition"]["paths"]) == UNSORTED_SPEC_PATHS


class TestDelete:
    def test_the_stored_document_is_removed(self):
        tk.get_action("apidocs_schema_update")(
            _sysadmin_context(), {"definition": dict(MINIMAL_SPEC)}
        )

        assert (
            tk.get_action("apidocs_schema_delete")(_sysadmin_context(), {}) is True
        )
        assert ApidocsSchema.get() is None

    def test_deleting_without_a_stored_document_is_not_found(self):
        with pytest.raises(tk.ObjectNotFound):
            tk.get_action("apidocs_schema_delete")(_sysadmin_context(), {})
