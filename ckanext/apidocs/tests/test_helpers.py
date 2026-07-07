"""Tests for helpers.py."""

from ckanext.apidocs import helpers


def test_collect_core_actions_contains_known_actions():
    actions = helpers.collect_core_actions()
    # Core CKAN should include package_show and package_create
    assert "package_show" in actions
    assert "package_create" in actions


def test_build_openapi_contains_paths():
    spec = helpers.build_openapi_spec()
    paths = spec.get("paths", {})
    assert "/api/3/action/package_show" in paths
    assert "/api/3/action/package_create" in paths

    # security scheme and global security should be present
    assert "security" in spec
    assert isinstance(spec["security"], list)
    assert any(isinstance(item, dict) and "ApiKeyAuth" in item for item in spec["security"])  # type: ignore
    assert "securitySchemes" in spec["components"]
    assert "ApiKeyAuth" in spec["components"]["securitySchemes"]
    assert spec["components"]["securitySchemes"]["ApiKeyAuth"]["name"] == "Authorization"
    assert "CKAN API key" in spec["components"]["securitySchemes"]["ApiKeyAuth"]["description"] or "CKAN" in spec["components"]["securitySchemes"]["ApiKeyAuth"]["description"]


def test_dump_yaml_or_json():
    spec = helpers.build_openapi_spec()
    s = helpers.dump_openapi_yaml(spec)
    assert "openapi" in s
    assert "package_show" in s
    # ensure the YAML contains the Authorization header name from the security scheme
    assert "Authorization" in s
