"""stamp template slug/name/resolved_spec onto workshop instances

Makes each WorkshopInstance self-describing by denormalizing the source
template at launch time. This decouples an instance from its template row,
which is a prerequisite for moving templates to git-managed YAML and dropping
the workshops table as a mutable entity (see ADR-0006).

Existing rows are backfilled from the still-present workshops FK. The backfill
is best-effort for historical instances: a template may have changed since the
instance launched, so the reconstructed resolved_spec reflects the template's
*current* definition, not necessarily what that instance actually ran. New
launches stamp the exact resolved spec.

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-06-15 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "d4e5f6a7b8c9"
down_revision: str | None = "c3d4e5f6a7b8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "workshop_instances",
        sa.Column("template_slug", sa.String(length=63), nullable=True),
    )
    op.add_column(
        "workshop_instances",
        sa.Column("template_name", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "workshop_instances",
        sa.Column(
            "resolved_spec",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
    )

    # Backfill from the source template (FK still present at this revision).
    op.execute(
        """
        UPDATE workshop_instances wi SET
            template_slug = w.slug,
            template_name = w.name,
            resolved_spec = jsonb_build_object(
                'image', w.image,
                'port', w.port,
                'duration', wi.duration_requested,
                'env', COALESCE(w.env, '{}'::jsonb),
                'args', COALESCE(to_jsonb(w.args), '[]'::jsonb),
                'resources', w.resources,
                'storage', w.storage
            )
        FROM workshops w
        WHERE wi.workshop_id = w.id
        """
    )

    op.alter_column("workshop_instances", "template_slug", nullable=False)
    op.alter_column("workshop_instances", "template_name", nullable=False)
    op.alter_column("workshop_instances", "resolved_spec", nullable=False)
    op.create_index(
        "ix_workshop_instances_template_slug",
        "workshop_instances",
        ["template_slug"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_workshop_instances_template_slug",
        table_name="workshop_instances",
    )
    op.drop_column("workshop_instances", "resolved_spec")
    op.drop_column("workshop_instances", "template_name")
    op.drop_column("workshop_instances", "template_slug")
