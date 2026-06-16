"""drop the workshop_instances -> workshops foreign key

In file-template mode (ADR-0006), a template's id is a deterministic uuid5 with
no row in the workshops table, so an instance's workshop_id would violate the
FK. Instances are already self-describing (template_slug + resolved_spec are
stamped at launch), and the stable id keeps per-template stats coherent, so the
constraint is no longer needed. The column stays for now (it is removed/renamed
to template_slug when the table is dropped in a later phase).

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-06-16 00:00:00.000000

"""

from collections.abc import Sequence

from alembic import op

revision: str = "f6a7b8c9d0e1"
down_revision: str | None = "e5f6a7b8c9d0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_FK_NAME = "workshop_instances_workshop_id_fkey"


def upgrade() -> None:
    op.execute(f"ALTER TABLE workshop_instances DROP CONSTRAINT IF EXISTS {_FK_NAME}")


def downgrade() -> None:
    op.create_foreign_key(
        _FK_NAME,
        "workshop_instances",
        "workshops",
        ["workshop_id"],
        ["id"],
    )
