"""Create apidocs_schema and apidocs_schema_state tables.

Revision ID: a1c3f7d92b4e
Revises:
Create Date: 2026-09-21 10:12:41.482130

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, used by Alembic.
revision = "a1c3f7d92b4e"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "apidocs_schema",
        sa.Column("name", sa.Text, primary_key=True),
        sa.Column("updated", sa.TIMESTAMP(timezone=True)),
        sa.Column("definition", JSONB, nullable=False),
    )
    op.create_index("ix_apidocs_schema_updated", "apidocs_schema", ["updated"])

    op.create_table(
        "apidocs_schema_state",
        sa.Column("name", sa.Text, primary_key=True),
        sa.Column("version", sa.Integer, nullable=False, server_default="0"),
        sa.Column("updated", sa.TIMESTAMP(timezone=True), nullable=False),
    )


def downgrade():
    op.drop_table("apidocs_schema_state")
    op.drop_index("ix_apidocs_schema_updated", table_name="apidocs_schema")
    op.drop_table("apidocs_schema")
