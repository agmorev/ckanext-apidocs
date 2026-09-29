"""Tests for ckanext.apidocs.utils."""

from __future__ import annotations

import logging

import pytest

import ckan.plugins as p

from ckanext.apidocs.utils import actions, docstring


DOCSTRING = """
Return the metadata of a dataset.

A longer description
spanning two lines.

:param id: the id or name of the dataset
:type id: string
:param include_data: include the internal data
    (sysadmin only)
:type: include_data: bool
:returns: the dataset
:rtype: dictionary
"""


class FakeActionsPlugin:
    name = "fake"

    def get_actions(self):
        return {"fake_thing": _fake_thing, "fake_list": _fake_list}


class BrokenActionsPlugin:
    name = "broken"

    def get_actions(self):
        raise RuntimeError("boom")


class WeirdActionsPlugin:
    name = "weird"

    def get_actions(self):
        return {"weird_action": "not a callable"}


def _fake_thing(context, data_dict):
    return {}


def _fake_list(context, data_dict):
    return []


def _implementations(interface, *plugins):
    def implementations(interface_):
        return list(plugins) if interface_ is interface else []

    return implementations


# parse_docstring


def test_parse_docstring_extracts_summary_description_and_params():
    parsed = docstring.parse_docstring(DOCSTRING)

    assert parsed.summary == "Return the metadata of a dataset."
    assert parsed.description == "A longer description\nspanning two lines."
    assert set(parsed.params) == {"id", "include_data"}
    assert parsed.params["id"].type == "string"
    assert parsed.params["id"].description == "the id or name of the dataset"
    # ``:type: name: type`` is a typo present in CKAN's own docstrings
    assert parsed.params["include_data"].type == "bool"
    assert (
        parsed.params["include_data"].description
        == "include the internal data (sysadmin only)"
    )
    assert parsed.returns == "the dataset"
    assert parsed.returns_type == "dictionary"


def test_summary_joins_the_wrapped_lines_of_the_first_paragraph():
    parsed = docstring.parse_docstring(
        "Show the data from an item of 'activity' (part of the activity\n"
        "stream).\n"
        "\n"
        ":param id: the id of the activity\n"
        ":type id: string\n"
    )

    assert parsed.summary == (
        "Show the data from an item of 'activity' "
        "(part of the activity stream)."
    )
    assert parsed.description == ""
    assert parsed.params["id"].description == "the id of the activity"


def test_summary_stops_at_the_first_paragraph():
    parsed = docstring.parse_docstring(
        "Summary wrapped\n"
        "over two lines.\n"
        "\n"
        "A real description\n"
        "spanning lines.\n"
        "\n"
        ":param id: the id\n"
    )

    assert parsed.summary == "Summary wrapped over two lines."
    assert parsed.description == "A real description\nspanning lines."


def test_summary_stops_at_the_directives_without_a_blank_line():
    parsed = docstring.parse_docstring(
        "Summary wrapped\nover two lines.\n:param id: the id\n"
    )

    assert parsed.summary == "Summary wrapped over two lines."
    assert parsed.description == ""
    assert parsed.params["id"].description == "the id"


def test_returns_text_does_not_leak_into_parameters():
    parsed = docstring.parse_docstring(
        "Summary.\n"
        "\n"
        ":param id: the id\n"
        ":type id: string\n"
        ":returns: the dataset\n"
        ":rtype: dict\n"
    )

    assert parsed.params["id"].description == "the id"
    assert "the dataset" not in parsed.params["id"].description
    assert parsed.returns == "the dataset"


def test_parameter_types_with_multiple_words():
    parsed = docstring.parse_docstring(
        "Summary.\n"
        "\n"
        ":param list of strings ids: the ids\n"
        ":type ids: list of strings\n"
    )

    assert parsed.params["ids"].type == "list of strings"


def test_required_parameters_are_detected():
    parsed = docstring.parse_docstring(
        "Summary.\n"
        "\n"
        ":param id: the id of the dataset (required)\n"
        ":param q: the query (not required)\n"
    )

    assert parsed.params["id"].required is True
    assert parsed.params["q"].required is False


def test_parse_docstring_renders_notes_and_raises():
    parsed = docstring.parse_docstring(
        "Summary.\n"
        "\n"
        ".. note:: Only sysadmins can use this.\n"
        ":raises ValueError: if the id is invalid\n"
    )

    assert "**Note** Only sysadmins can use this." in parsed.description
    assert "**Raises** ValueError - if the id is invalid" in parsed.description


@pytest.mark.parametrize("value", [None, "", "\n\n", "   "])
def test_parse_docstring_handles_empty_input(value):
    parsed = docstring.parse_docstring(value)

    assert parsed.summary == ""
    assert parsed.description == ""
    assert parsed.params == {}
    assert parsed.returns == ""


def test_parse_docstring_ignores_malformed_directives():
    parsed = docstring.parse_docstring(
        "Summary.\n\n:param without colon\n:type\n:returns\n"
    )

    assert parsed.summary == "Summary."
    assert parsed.params == {}


def test_params_dict_exposes_plain_dicts():
    params = docstring.parse_docstring(DOCSTRING).params_dict()

    assert params["id"] == {
        "name": "id",
        "type": "string",
        "description": "the id or name of the dataset",
        "required": False,
    }


# infer_method


def test_infer_method_from_module_name():
    def action(context, data_dict):
        pass

    action.__module__ = "ckan.logic.action.update"

    assert actions.infer_method("some_action", action) == "PUT"


def test_infer_method_from_side_effect_free_marker():
    def action(context, data_dict):
        pass

    action.side_effect_free = True  # type: ignore[attr-defined]

    assert actions.infer_method("some_action", action) == "GET"


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("package_list", "GET"),
        ("package_show", "GET"),
        ("package_search", "GET"),
        ("user_autocomplete", "GET"),
        ("package_create", "POST"),
        ("mystery", "POST"),
    ],
)
def test_infer_method_from_action_name(name, expected):
    def action(context, data_dict):
        pass

    assert actions.infer_method(name, action) == expected


def test_infer_method_respects_the_explicit_attribute():
    def action(context, data_dict):
        pass

    action.apidocs_method = "patch"  # type: ignore[attr-defined]

    assert actions.infer_method("package_show", action) == "PATCH"


# collect_actions


def test_collect_actions_includes_core_and_plugin_actions(monkeypatch):
    monkeypatch.setattr(
        p, "PluginImplementations", _implementations(p.IActions, FakeActionsPlugin())
    )

    collected = actions.collect_actions()

    assert collected["package_show"].method == "GET"
    assert collected["package_show"].origin == actions.CORE_ORIGIN
    assert collected["package_show"].module == "get"
    assert collected["package_create"].method == "POST"
    assert collected["fake_list"].method == "GET"
    assert collected["fake_thing"].method == "POST"
    assert collected["fake_list"].origin == "fake"


def test_collect_actions_can_exclude_plugins(monkeypatch):
    monkeypatch.setattr(
        p, "PluginImplementations", _implementations(p.IActions, FakeActionsPlugin())
    )

    collected = actions.collect_actions(exclude_extensions=["fake"])

    assert "fake_thing" not in collected
    assert "package_show" in collected


def test_collect_actions_can_restrict_plugins(monkeypatch):
    monkeypatch.setattr(
        p, "PluginImplementations", _implementations(p.IActions, FakeActionsPlugin())
    )

    collected = actions.collect_actions(include_extensions=["other"])

    assert "fake_thing" not in collected
    assert "package_show" in collected


def test_collect_actions_logs_and_skips_broken_plugins(monkeypatch, log_capture):
    monkeypatch.setattr(
        p,
        "PluginImplementations",
        _implementations(p.IActions, BrokenActionsPlugin()),
    )

    with log_capture(actions.__name__) as records:
        collected = actions.collect_actions()

    assert "package_show" in collected
    assert any(
        "Failed to collect actions" in record.getMessage()
        for record in records
    )
    assert any(record.levelno == logging.ERROR for record in records)


def test_collect_actions_skips_non_callable_actions(monkeypatch):
    monkeypatch.setattr(
        p,
        "PluginImplementations",
        _implementations(p.IActions, WeirdActionsPlugin()),
    )

    collected = actions.collect_actions()

    assert "weird_action" not in collected


def test_collect_actions_returns_actions_sorted_by_name():
    names = list(actions.collect_actions())

    assert names == sorted(names)


def test_actions_carry_badges():
    collected = actions.collect_actions()

    badges = collected["package_show"].badges()

    assert "core" in badges


# configuration helpers


@pytest.mark.ckan_config("ckanext.apidocs.enable_api_methods", "get post")
def test_get_api_methods_reads_the_configuration(ckan_config):
    assert [method["name"] for method in actions.get_api_methods()] == [
        "GET",
        "POST",
    ]
