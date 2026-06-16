"""drop the workshops (template) table

Templates are now git-managed YAML served from an in-memory registry (ADR-0006),
so the workshops table is no longer the source of truth. Instances remain
self-describing (template_slug + resolved_spec stamped at launch) and keep
referencing their template by the stable id stored in workshop_id, so per-template
stats continue to work without the table.

DATA LOSS: this drops all rows in the workshops table. Port any database-only
templates into deploy/charts/orchestra/files/templates/*.yaml before applying.

Revision ID: a7b8c9d0e1f2
Revises: f6a7b8c9d0e1
Create Date: 2026-06-16 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "a7b8c9d0e1f2"
down_revision: str | None = "f6a7b8c9d0e1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_table("workshops")


def downgrade() -> None:
    # Recreate the table structure (empty). The FK from workshop_instances was
    # already dropped in f6a7b8c9d0e1 and is not restored here.
    op.create_table(
        "workshops",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("slug", sa.String(length=63), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("image", sa.String(length=500), nullable=False),
        sa.Column("default_duration", sa.String(length=20), nullable=False),
        sa.Column("port", sa.Integer(), nullable=False),
        sa.Column("tier", sa.String(length=20), nullable=False, server_default="small"),
        sa.Column("env", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("args", postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column("resources", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("storage", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("ingress", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("tags", postgresql.ARRAY(sa.String()), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_by", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
    )
