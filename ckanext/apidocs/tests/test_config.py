"""Tests for ckanext.apidocs.config."""

from __future__ import annotations

import pytest

from ckanext.apidocs import config


def test_allowed_users_is_empty_by_default(ckan_config):
    assert config.apidocs_allowed_users() == []


def test_allowed_users_parses_the_config_option(ckan_config):
    with pytest.MonkeyPatch.context() as patch:
        patch.setitem(
            ckan_config, "ckanext.apidocs.allowed_users", "editor api_bot"
        )

        assert config.apidocs_allowed_users() == ["editor", "api_bot"]


def test_every_user_is_allowed_without_the_allowlist(ckan_config):
    assert config.apidocs_allows_user("editor")
    assert config.apidocs_allows_user("anyone")
    assert config.apidocs_allows_user(None)


def test_allowed_users_only_match_the_listed_names(ckan_config):
    with pytest.MonkeyPatch.context() as patch:
        patch.setitem(ckan_config, "ckanext.apidocs.allowed_users", "editor")

        assert config.apidocs_allows_user("editor")
        assert not config.apidocs_allows_user("someone-else")
        assert not config.apidocs_allows_user(None)
        assert not config.apidocs_allows_user("")


def test_allowed_users_ignore_the_name_case(ckan_config):
    with pytest.MonkeyPatch.context() as patch:
        patch.setitem(ckan_config, "ckanext.apidocs.allowed_users", "Editor")

        assert config.apidocs_allows_user("editor")
        assert config.apidocs_allows_user("EDITOR")


def test_sysadmin_only_is_disabled_by_default(ckan_config):
    assert not config.apidocs_sysadmin_only()
    assert config.apidocs_allows_user("anyone")
    assert config.apidocs_allows_user("anyone", sysadmin=True)


def test_sysadmin_only_only_allows_sysadmins(ckan_config):
    with pytest.MonkeyPatch.context() as patch:
        patch.setitem(ckan_config, "ckanext.apidocs.sysadmin_only", True)

        assert config.apidocs_sysadmin_only()
        assert config.apidocs_allows_user("someone", sysadmin=True)
        assert not config.apidocs_allows_user("someone")
        assert not config.apidocs_allows_user(None)


def test_sysadmin_only_takes_precedence_over_the_allowlist(ckan_config):
    with pytest.MonkeyPatch.context() as patch:
        patch.setitem(ckan_config, "ckanext.apidocs.sysadmin_only", True)
        patch.setitem(ckan_config, "ckanext.apidocs.allowed_users", "editor")

        assert config.apidocs_allows_user("someone", sysadmin=True)
        assert not config.apidocs_allows_user("editor")


def test_access_is_public_when_nothing_is_configured(ckan_config):
    assert not config.apidocs_access_restricted()


@pytest.mark.parametrize(
    "key,value",
    [
        ("ckanext.apidocs.require_login", True),
        ("ckanext.apidocs.sysadmin_only", True),
        ("ckanext.apidocs.allowed_users", "editor"),
    ],
)
def test_access_is_restricted_when_an_option_is_set(ckan_config, key, value):
    with pytest.MonkeyPatch.context() as patch:
        patch.setitem(ckan_config, key, value)

        assert config.apidocs_access_restricted()
