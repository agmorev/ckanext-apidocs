"""Tests for ckanext.apidocs.helpers."""

from __future__ import annotations

import pytest

import ckan.plugins as p
from ckan.plugins import toolkit as tk

from ckanext.apidocs import helpers
from ckanext.apidocs.schemas import schema

from .test_utils import FakeActionsPlugin, _implementations


# specification generation


def test_build_openapi_spec_documents_get_actions():
    spec = helpers.build_openapi_spec()

    assert spec["openapi"] == "3.0.0"
    assert spec["servers"] == [{"url": "/api/3/action"}]
    assert spec["info"]["title"] == "CKAN API"
    assert "ApiKeyAuth" in spec["components"]["securitySchemes"]
    assert "Error" in spec["components"]["schemas"]

    operation = spec["paths"]["/package_show"]["get"]

    assert operation["operationId"] == "package_show"
    assert operation["tags"] == ["GET"]
    assert operation["security"] == [{"ApiKeyAuth": []}]
    assert "core" in operation["x-badges"]
    assert operation["externalDocs"]["url"].endswith(
        "#ckan.logic.action.get.package_show"
    )

    names = [parameter["name"] for parameter in operation["parameters"]]
    assert "id" in names

    error = operation["responses"]["400"]["content"]["application/json"]
    assert error["schema"]["$ref"] == "#/components/schemas/Error"


def test_build_openapi_spec_documents_post_actions():
    spec = helpers.build_openapi_spec()

    operation = spec["paths"]["/package_create"]["post"]

    assert operation["operationId"] == "package_create"
    assert "parameters" not in operation
    assert operation["security"] == [{"ApiKeyAuth": []}]

    body = operation["requestBody"]["content"]["application/json"]["schema"]
    assert "title" in body["properties"]


def test_build_openapi_spec_is_idempotent():
    assert helpers.build_openapi_spec() == helpers.build_openapi_spec()


def test_spec_generation_does_not_use_module_level_state():
    helpers.build_openapi_spec()

    # The old implementation kept the document in a module level dictionary
    # and returned shallow copies of it, so paths leaked between calls.
    assert not hasattr(schema, "spec")
    assert not hasattr(schema, "operation")


def test_spec_does_not_leak_between_calls():
    tk.config["ckanext.apidocs.enable_api_methods"] = "GET"
    only_get = helpers.build_openapi_spec()
    del tk.config["ckanext.apidocs.enable_api_methods"]
    everything = helpers.build_openapi_spec()

    assert "/package_show" in only_get["paths"]
    assert "/package_create" not in only_get["paths"]
    assert "/package_create" in everything["paths"]


@pytest.mark.ckan_config("ckanext.apidocs.base_path", "/api/4/action")
def test_base_path_comes_from_the_configuration(ckan_config):
    assert helpers.build_openapi_spec()["servers"] == [{"url": "/api/4/action"}]


@pytest.mark.ckan_config("ckanext.apidocs.openapi_version", "3.1.0")
def test_openapi_version_comes_from_the_configuration(ckan_config):
    assert helpers.build_openapi_spec()["openapi"] == "3.1.0"


@pytest.mark.ckan_config("ckanext.apidocs.enable_api_methods", "GET")
def test_disabled_methods_are_not_documented(ckan_config):
    spec = helpers.build_openapi_spec()

    assert [tag["name"] for tag in spec["tags"]] == ["GET"]
    assert "/package_show" in spec["paths"]
    assert "/package_create" not in spec["paths"]


@pytest.mark.ckan_config("ckanext.apidocs.exclude_extensions", "fake")
def test_excluded_extensions_are_not_documented(ckan_config, monkeypatch):
    monkeypatch.setattr(
        p,
        "PluginImplementations",
        _implementations(p.IActions, FakeActionsPlugin()),
    )

    spec = helpers.build_openapi_spec()

    assert "/fake_thing" not in spec["paths"]
    assert "/package_show" in spec["paths"]


@pytest.mark.ckan_config("ckanext.apidocs.include_extensions", "other")
def test_only_included_extensions_are_documented(ckan_config, monkeypatch):
    monkeypatch.setattr(
        p,
        "PluginImplementations",
        _implementations(p.IActions, FakeActionsPlugin()),
    )

    spec = helpers.build_openapi_spec()

    assert "/fake_thing" not in spec["paths"]
    assert "/package_show" in spec["paths"]


@pytest.mark.ckan_config("ckanext.apidocs.exclude_extensions", "fake")
def test_explicit_extensions_override_the_configuration(
    ckan_config, monkeypatch
):
    monkeypatch.setattr(
        p,
        "PluginImplementations",
        _implementations(p.IActions, FakeActionsPlugin()),
    )

    spec = helpers.build_openapi_spec(exclude_extensions=[])

    assert "/fake_thing" in spec["paths"]


@pytest.mark.ckan_config("ckanext.apidocs.title", "My API")
@pytest.mark.ckan_config("ckanext.apidocs.spec_version", "9.9.9")
@pytest.mark.ckan_config("ckanext.apidocs.token_header", "X-API-Key")
def test_metadata_comes_from_the_configuration(ckan_config):
    spec = helpers.build_openapi_spec()

    assert spec["info"]["title"] == "My API"
    assert spec["info"]["version"] == "9.9.9"
    assert (
        spec["components"]["securitySchemes"]["ApiKeyAuth"]["name"]
        == "X-API-Key"
    )


def test_build_openapi_spec_accepts_overrides():
    spec = helpers.build_openapi_spec(
        base_path="/custom",
        version="1.2.3",
        title="Overridden",
        methods=["GET"],
    )

    assert spec["servers"] == [{"url": "/custom"}]
    assert spec["info"]["title"] == "Overridden"
    assert spec["info"]["version"] == "1.2.3"
    assert "/package_create" not in spec["paths"]


# caching


def test_get_openapi_spec_uses_the_cache(monkeypatch):
    calls = []

    def counting_builder(**kwargs):
        calls.append(1)
        return {}

    monkeypatch.setattr(helpers, "build_openapi_spec", counting_builder)

    helpers.get_openapi_spec()
    helpers.get_openapi_spec()

    assert len(calls) == 1


def test_invalidate_cache_forces_a_rebuild(monkeypatch):
    calls = []

    def counting_builder(**kwargs):
        calls.append(1)
        return {}

    monkeypatch.setattr(helpers, "build_openapi_spec", counting_builder)

    helpers.get_openapi_spec()
    helpers.invalidate_cache()
    helpers.get_openapi_spec()

    assert len(calls) == 2


@pytest.mark.ckan_config("ckanext.apidocs.cache_ttl", "0")
def test_zero_ttl_disables_the_cache(ckan_config, monkeypatch):
    calls = []

    def counting_builder(**kwargs):
        calls.append(1)
        return {}

    monkeypatch.setattr(helpers, "build_openapi_spec", counting_builder)

    helpers.get_openapi_spec()
    helpers.get_openapi_spec()

    assert len(calls) == 2


def test_cached_spec_is_not_shared_with_the_caller():
    first = helpers.get_openapi_spec()
    first["openapi"] = "mutated"

    assert helpers.get_openapi_spec()["openapi"] == "3.0.0"


# serialization


def test_dumps_openapi_json():
    payload = helpers.dumps_openapi_json(helpers.build_openapi_spec())

    assert '"openapi": "3.0.0"' in payload
    assert '"/package_show"' in payload


def test_dump_openapi_yaml():
    yaml = pytest.importorskip("yaml")

    payload = helpers.dump_openapi_yaml(helpers.build_openapi_spec())
    loaded = yaml.safe_load(payload)

    assert loaded["openapi"] == "3.0.0"
    assert "/package_show" in loaded["paths"]


def test_spec_etag_changes_with_the_payload():
    payload = helpers.dumps_openapi_json(helpers.build_openapi_spec())

    assert helpers.spec_etag(payload) == helpers.spec_etag(payload)
    assert helpers.spec_etag(payload) != helpers.spec_etag(payload + " ")


# badges


def test_collect_badges_indexes_operations_by_path_and_method():
    spec = helpers.build_openapi_spec()

    badges = helpers.collect_badges(spec)

    assert "core" in badges["/package_show"]["get"]
    assert helpers.collect_badges({"paths": {}}) == {}


def test_collect_badges_ignores_operations_without_badges():
    spec = {
        "paths": {
            "/example": {"get": {"operationId": "example"}},
            "/hidden": {"get": {"x-badges": []}},
        }
    }

    assert helpers.collect_badges(spec) == {}
