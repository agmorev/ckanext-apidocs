"""Actions managing the OpenAPI document edited by sysadmins.

The stored document replaces the document generated from the registered
actions. Removing it switches the documentation back to the generated one.
All the actions are sysadmin-only.
"""

from __future__ import annotations

from typing import Any

import ckan.plugins.toolkit as tk
from ckan.logic import validate

from ckanext.apidocs.logic import schema
from ckanext.apidocs.model import ApidocsSchema


@validate(schema.apidocs_schema_update)
def apidocs_schema_update(
    context: Any, data_dict: dict[str, Any]
) -> dict[str, Any]:
    """Store the OpenAPI document used by the documentation.

    The document replaces the one generated from the registered actions and
    is served by every documentation endpoint until it is removed with
    :func:`apidocs_schema_delete`.

    :param definition: the OpenAPI document, either as a mapping or as a
        JSON/YAML string. It must be an OpenAPI 3.x document with the
        ``openapi``, ``info`` and ``paths`` keys
    :type definition: dict
    :returns: the stored document together with its metadata
    :rtype: dict
    """
    tk.check_access("apidocs_schema_update", context, data_dict)

    row = ApidocsSchema.set_definition(data_dict["definition"])

    return row.as_dict()


@tk.side_effect_free
def apidocs_schema_show(context: Any, data_dict: dict[str, Any]) -> dict[str, Any]:
    """Return the stored OpenAPI document.

    :returns: the stored document together with its metadata, or an empty
        dictionary when the documentation is generated from the registered
        actions
    :rtype: dict
    """
    tk.check_access("apidocs_schema_show", context, data_dict)

    row = ApidocsSchema.get()

    if row is None:
        return {}

    return row.as_dict()


def apidocs_schema_delete(context: Any, data_dict: dict[str, Any]) -> bool:
    """Remove the stored OpenAPI document.

    The documentation is generated from the registered actions again, as if
    no document had ever been stored.

    :returns: ``True``
    :rtype: bool
    """
    tk.check_access("apidocs_schema_delete", context, data_dict)

    row = ApidocsSchema.get()

    if row is None:
        raise tk.ObjectNotFound(
            tk._("No stored API documentation schema found")
        )

    row.delete()

    return True
