"""Web views of ckanext-apidocs.

``views.docs``
    The documentation itself: the Swagger UI page and the OpenAPI documents
    served at ``/api/docs/``.

``views.admin``
    The sysadmin page managing the stored OpenAPI document, mounted at
    ``/ckan-admin/apidocs``.
"""

from __future__ import annotations

from flask import Blueprint

from ckanext.apidocs.views import admin, docs


def get_blueprints() -> list[Blueprint]:
    """The blueprints registered by the plugin."""
    return [docs.bp, admin.bp]
