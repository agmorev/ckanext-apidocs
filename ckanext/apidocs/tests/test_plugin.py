"""Tests for ckanext.apidocs.plugin."""

from __future__ import annotations

import pytest

import ckan.logic as logic
from ckan import plugins as p
from ckan.config.declaration import Declaration, Key
from ckan.plugins import toolkit as tk

from ckanext.apidocs import config, plugin


CONFIG_OPTIONS = [
    "ckanext.apidocs.base_path",
    "ckanext.apidocs.openapi_version",
    "ckanext.apidocs.enable_api_methods",
    "ckanext.apidocs.title",
    "ckanext.apidocs.description",
    "ckanext.apidocs.spec_version",
    "ckanext.apidocs.token_header",
    "ckanext.apidocs.cache_ttl",
    "ckanext.apidocs.require_login",
    "ckanext.apidocs.sysadmin_only",
    "ckanext.apidocs.allowed_users",
    "ckanext.apidocs.include_extensions",
    "ckanext.apidocs.exclude_extensions",
    "ckanext.apidocs.ui.validator_url",
    "ckanext.apidocs.ui.persist_authorization",
    "ckanext.apidocs.ui.doc_expansion",
    "ckanext.apidocs.ui.filter",
    "ckanext.apidocs.ui.try_it_out",
    "ckanext.apidocs.ui.deep_linking",
]

DECLARED_DEFAULTS = {
    "ckanext.apidocs.base_path": config.DEFAULT_BASE_PATH,
    "ckanext.apidocs.openapi_version": config.DEFAULT_OPENAPI_VERSION,
    "ckanext.apidocs.enable_api_methods": config.DEFAULT_METHODS,
    "ckanext.apidocs.title": "CKAN API",
    "ckanext.apidocs.spec_version": config.CKAN_VERSION,
    "ckanext.apidocs.token_header": config.DEFAULT_TOKEN_HEADER,
    "ckanext.apidocs.cache_ttl": config.DEFAULT_CACHE_TTL,
    "ckanext.apidocs.require_login": False,
    "ckanext.apidocs.sysadmin_only": False,
    "ckanext.apidocs.ui.persist_authorization": True,
    "ckanext.apidocs.ui.doc_expansion": config.DEFAULT_DOC_EXPANSION,
    "ckanext.apidocs.ui.filter": True,
    "ckanext.apidocs.ui.try_it_out": True,
    "ckanext.apidocs.ui.deep_linking": True,
}


def _declare_config_options() -> Declaration:
    """Load the declaration of the plugin from ``config_declaration.yaml``."""
    declaration = Declaration()

    plugin.ApidocsPlugin().declare_config_options(declaration, Key())

    return declaration


@pytest.mark.ckan_config("ckan.plugins", "apidocs")
@pytest.mark.usefixtures("with_plugins")
def test_plugin_is_loaded():
    assert p.plugin_loaded("apidocs")


def test_plugin_implements_the_expected_interfaces():
    for interface in (
        p.IConfigurer,
        p.IConfigDeclaration,
        p.IBlueprint,
        p.IClick,
        p.IActions,
        p.IAuthFunctions,
        p.IValidators,
    ):
        assert interface.implemented_by(plugin.ApidocsPlugin), interface


def test_plugin_declares_the_configuration():
    declaration = _declare_config_options()

    for option in CONFIG_OPTIONS:
        assert declaration.get(option) is not None, option


def test_declared_defaults_match_the_config_module():
    declaration = _declare_config_options()

    for option, expected in DECLARED_DEFAULTS.items():
        declared = declaration.get(option)

        assert declared is not None, option
        assert declared.default == expected, option


@pytest.mark.ckan_config("ckan.plugins", "apidocs")
@pytest.mark.usefixtures("with_plugins")
def test_config_declaration_is_loaded_by_ckan():
    declaration = Declaration()
    declaration.setup()

    for option in CONFIG_OPTIONS:
        assert declaration.get(option) is not None, option


@pytest.mark.ckan_config("ckan.plugins", "apidocs")
@pytest.mark.usefixtures("with_plugins")
def test_example_actions_are_not_registered():
    # building the registry through the public API
    tk.get_action("package_show")

    assert "apidocs_example" not in logic._actions
    assert "example_get_sum" not in logic._actions


@pytest.mark.ckan_config("ckan.plugins", "apidocs")
@pytest.mark.usefixtures("with_plugins")
def test_schema_actions_are_registered():
    for action in (
        "apidocs_schema_update",
        "apidocs_schema_show",
        "apidocs_schema_delete",
    ):
        assert action in logic._actions, action


@pytest.mark.ckan_config("ckan.plugins", "apidocs")
@pytest.mark.usefixtures("with_plugins")
def test_the_document_validator_is_registered():
    from ckan.logic import get_validator

    assert get_validator("apidocs_definition_valid")
