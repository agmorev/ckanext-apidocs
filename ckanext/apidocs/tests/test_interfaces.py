"""Tests for the ``IApidocs`` extension point."""

from __future__ import annotations

from ckan import plugins as p

from ckanext.apidocs import helpers, interfaces


class BadgesPlugin:
    name = "badges"

    def get_action_badges(self, action_name, origin=None):
        return ["custom"] if action_name == "package_show" else None


class SpecPlugin:
    name = "spec"

    def modify_openapi_spec(self, spec):
        spec["info"]["x-modified-by"] = "spec"
        return spec


class BrokenPlugin:
    name = "broken"

    def get_action_badges(self, action_name, origin=None):
        raise RuntimeError("boom")

    def modify_openapi_spec(self, spec):
        raise RuntimeError("boom")


def _use_plugins(monkeypatch, *plugins):
    def implementations(interface):
        return list(plugins) if interface is interfaces.IApidocs else []

    monkeypatch.setattr(p, "PluginImplementations", implementations)


def test_interface_is_a_ckan_interface():
    assert issubclass(interfaces.IApidocs, p.Interface)


def test_plugins_can_modify_the_openapi_document(monkeypatch):
    _use_plugins(monkeypatch, SpecPlugin())

    spec = helpers.build_openapi_spec()

    assert spec["info"]["x-modified-by"] == "spec"


def test_plugins_can_add_action_badges(monkeypatch):
    _use_plugins(monkeypatch, BadgesPlugin())

    spec = helpers.build_openapi_spec()
    badges = spec["paths"]["/package_show"]["get"]["x-badges"]

    assert "custom" in badges
    assert "core" in badges


def test_broken_plugins_do_not_break_the_document(monkeypatch, log_capture):
    _use_plugins(monkeypatch, BrokenPlugin())

    with log_capture(helpers.__name__) as records:
        spec = helpers.build_openapi_spec()

    assert "/package_show" in spec["paths"]
    assert any("IApidocs" in record.getMessage() for record in records)
