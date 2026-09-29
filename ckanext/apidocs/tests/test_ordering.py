"""Tests for ckanext.apidocs.utils.ordering."""

from __future__ import annotations

from ckanext.apidocs.utils.ordering import canonical_definition
from ckanext.apidocs.tests.data import (
    UNSORTED_SPEC,
    UNSORTED_SPEC_KEYS,
    UNSORTED_SPEC_PATHS,
)


def test_object_keys_are_sorted_alphabetically():
    assert list(canonical_definition({"b": 1, "a": 2})) == ["a", "b"]


def test_nested_objects_are_sorted_recursively():
    ordered = canonical_definition({"b": {"d": 1, "c": 2}})

    assert list(ordered["b"]) == ["c", "d"]


def test_the_document_is_sorted_at_every_level():
    ordered = canonical_definition(UNSORTED_SPEC)

    assert list(ordered) == UNSORTED_SPEC_KEYS
    assert list(ordered["paths"]) == UNSORTED_SPEC_PATHS
    assert list(ordered["info"]) == ["title", "version"]
    assert list(ordered["paths"]["/zulu"]["post"]) == ["responses", "summary"]


def test_lists_keep_their_order():
    ordered = canonical_definition(
        {"tags": [{"name": "POST"}, {"name": "GET"}]}
    )

    assert [tag["name"] for tag in ordered["tags"]] == ["POST", "GET"]
    assert list(ordered["tags"][0]) == ["name"]


def test_values_are_kept():
    assert canonical_definition(UNSORTED_SPEC) == UNSORTED_SPEC


def test_the_document_passed_in_is_not_modified():
    document = {"b": 1, "a": {"d": 1, "c": 2}}

    canonical_definition(document)

    assert list(document) == ["b", "a"]
    assert list(document["a"]) == ["d", "c"]
