"""Authorization functions of the actions managing the OpenAPI document.

Every action is disabled on purpose: CKAN lets sysadmins through without
consulting the authorization functions, so ``{"success": False}`` makes these
actions available to sysadmins only.
"""

from __future__ import annotations

from ckan import types


def apidocs_schema_update(
    context: types.Context, data_dict: types.DataDict
) -> types.AuthResult:
    """Only sysadmins can store the OpenAPI document."""
    return {"success": False}


def apidocs_schema_show(
    context: types.Context, data_dict: types.DataDict
) -> types.AuthResult:
    """Only sysadmins can read the stored OpenAPI document."""
    return {"success": False}


def apidocs_schema_delete(
    context: types.Context, data_dict: types.DataDict
) -> types.AuthResult:
    """Only sysadmins can remove the stored OpenAPI document."""
    return {"success": False}
