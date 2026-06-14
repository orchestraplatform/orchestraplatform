"""add port to workshops

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-06-14 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = 'b2c3d4e5f6a7'
down_revision: str | None = 'a1b2c3d4e5f6'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        'workshops',
        sa.Column(
            'port',
            sa.Integer(),
            nullable=False,
            server_default='8787',
        ),
    )


def downgrade() -> None:
    op.drop_column('workshops', 'port')
