"""add tier to workshops

Adds the tenant node-pool tier (small/large) to workshop templates. The tier is
carried through to the Workshop CRD; the operator only maps it to
nodeSelector/tolerations when tenant pools are enabled (ADR-0005/0006). Existing
rows default to "small".

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-06-16 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "e5f6a7b8c9d0"
down_revision: str | None = "d4e5f6a7b8c9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "workshops",
        sa.Column(
            "tier",
            sa.String(length=20),
            nullable=False,
            server_default="small",
        ),
    )


def downgrade() -> None:
    op.drop_column("workshops", "tier")
