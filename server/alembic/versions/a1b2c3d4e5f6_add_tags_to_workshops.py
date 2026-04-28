"""add tags to workshops

Revision ID: a1b2c3d4e5f6
Revises: ff88c095ce42
Create Date: 2026-04-27 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = 'a1b2c3d4e5f6'
down_revision: str | None = 'ff88c095ce42'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        'workshops',
        sa.Column('tags', sa.ARRAY(sa.String()), nullable=False, server_default='{}'),
    )


def downgrade() -> None:
    op.drop_column('workshops', 'tags')
