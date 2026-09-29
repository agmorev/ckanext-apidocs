"""Database models backing the sysadmin editable OpenAPI document.

The document is stored as a single row of ``apidocs_schema``. The companion
``apidocs_schema_state`` table holds one tiny row per stored document with a
version counter that is bumped on every save and reset, so every worker
process can notice a change with a single cheap lookup instead of reading the
(potentially large) JSONB document.

The tables are created by the migrations of the extension::

    ckan -c /etc/ckan/default/ckan.ini db upgrade -p apidocs
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped

import ckan.plugins.toolkit as tk
from ckan import model

from ckanext.apidocs.utils.ordering import canonical_definition


#: Name of the stored OpenAPI document. A single document is supported, the
#: column exists so that more than one can be added without a migration.
DEFAULT_SCHEMA_NAME = "openapi"


def _current_datetime() -> datetime:
    return datetime.now(tz=timezone.utc)  # noqa: UP017


class ApidocsSchemaState(tk.BaseModel):
    """Change counter for the stored OpenAPI documents.

    Bumped explicitly by :meth:`ApidocsSchema.set_definition` and
    :meth:`ApidocsSchema.delete`.
    """

    __table__ = sa.Table(
        "apidocs_schema_state",
        tk.BaseModel.metadata,
        sa.Column("name", sa.Text, primary_key=True),
        sa.Column("version", sa.Integer, nullable=False, default=0),
        sa.Column(
            "updated",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            default=_current_datetime,
        ),
    )

    name: Mapped[str]
    version: Mapped[int]
    updated: Mapped[datetime]

    @classmethod
    def bump(cls, name: str) -> None:
        """Increase the version of a document, creating the row if needed."""
        row = model.Session.get(cls, name)

        if row is None:
            row = cls(name=name, version=0)
            model.Session.add(row)

        row.version += 1
        row.updated = _current_datetime()

    @classmethod
    def fingerprint(
        cls, name: str = DEFAULT_SCHEMA_NAME
    ) -> tuple[int, datetime | None]:
        """Cheap version of a stored document, ``(0, None)`` when absent."""
        row = model.Session.get(cls, name)

        if row is None:
            return 0, None

        return row.version, row.updated


class ApidocsSchema(tk.BaseModel):
    """The OpenAPI document stored by a sysadmin."""

    __table__ = sa.Table(
        "apidocs_schema",
        tk.BaseModel.metadata,
        sa.Column("name", sa.Text, primary_key=True),
        sa.Column(
            "updated",
            sa.TIMESTAMP(timezone=True),
            index=True,
            default=_current_datetime,
            onupdate=_current_datetime,
        ),
        sa.Column("definition", JSONB, nullable=False),
    )

    name: Mapped[str]
    updated: Mapped[datetime]
    definition: Mapped[dict[str, Any]]

    @classmethod
    def get(cls, name: str = DEFAULT_SCHEMA_NAME) -> ApidocsSchema | None:
        return model.Session.get(cls, name)

    @classmethod
    def set_definition(
        cls, definition: dict[str, Any], name: str = DEFAULT_SCHEMA_NAME
    ) -> ApidocsSchema:
        """Create or replace the stored document, returning the row.

        The definition is stored with every object key in alphabetical order,
        so the row stays readable in the database, see
        :func:`ckanext.apidocs.utils.ordering.canonical_definition`.
        """
        ordered = canonical_definition(definition)

        row = cls.get(name)

        if row is None:
            row = cls(name=name, definition=ordered)
            model.Session.add(row)
        else:
            row.definition = ordered

        ApidocsSchemaState.bump(name)
        model.Session.commit()

        return row

    def delete(self) -> None:
        """Remove the stored document so the generated one is served again."""
        model.Session.delete(self)
        ApidocsSchemaState.bump(self.name)
        model.Session.commit()

    @property
    def canonical_definition(self) -> dict[str, Any]:
        """The definition with every object key in alphabetical order.

        The order is restored on read: ``JSONB`` does not preserve the order
        the keys were stored in. ``paths`` come first alphabetically, which
        also orders the operations of every HTTP method section of the
        documentation, since the UI lists them in the order of ``paths``.
        """
        return canonical_definition(self.definition)

    def as_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "definition": self.canonical_definition,
            "updated": self.updated.isoformat(),
        }
