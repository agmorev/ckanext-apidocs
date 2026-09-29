"""Schemas of the actions storing the OpenAPI document."""

from __future__ import annotations

from ckan import types
from ckan.logic.schema import validator_args


@validator_args
def apidocs_schema_update(
    not_missing: types.Validator,
    apidocs_definition_valid: types.DataValidator,
) -> types.Schema:
    return {
        "definition": [not_missing, apidocs_definition_valid],
    }
