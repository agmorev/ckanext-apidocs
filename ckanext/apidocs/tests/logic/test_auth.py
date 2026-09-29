"""Tests for ckanext.apidocs.logic.auth."""

from __future__ import annotations

import pytest

import ckan.plugins.toolkit as tk
from ckan.tests import factories

from ckanext.apidocs.logic import auth
from ckanext.apidocs.tests.data import MINIMAL_SPEC


ACTIONS = ("apidocs_schema_update", "apidocs_schema_show", "apidocs_schema_delete")

pytestmark = [
    pytest.mark.ckan_config("ckan.plugins", "apidocs"),
    pytest.mark.usefixtures("with_plugins", "clean_db"),
]


@pytest.mark.parametrize("action", ACTIONS)
def test_the_authorization_functions_deny_everyone(action):
    # CKAN lets sysadmins through without consulting them
    assert getattr(auth, action)({}, {}) == {"success": False}


@pytest.mark.parametrize("action", ACTIONS)
def test_a_regular_user_is_not_authorized(action):
    context = {"user": factories.User()["name"]}

    with pytest.raises(tk.NotAuthorized):
        tk.get_action(action)(context, {"definition": dict(MINIMAL_SPEC)})


@pytest.mark.parametrize("action", ACTIONS)
def test_an_anonymous_user_is_not_authorized(action):
    with pytest.raises(tk.NotAuthorized):
        tk.get_action(action)({}, {"definition": dict(MINIMAL_SPEC)})


def test_a_sysadmin_is_authorized():
    context = {"user": factories.Sysadmin()["name"]}

    assert tk.get_action("apidocs_schema_show")(context, {}) == {}
