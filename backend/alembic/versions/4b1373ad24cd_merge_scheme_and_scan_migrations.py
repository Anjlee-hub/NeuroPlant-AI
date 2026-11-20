"""merge scheme and scan migrations

Revision ID: 4b1373ad24cd
Revises: a8c4e2f6b0d1, c7d1e3f5a9b2
Create Date: 2026-11-18 23:11:48.609999
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = '4b1373ad24cd'
down_revision: str | None = ('a8c4e2f6b0d1', 'c7d1e3f5a9b2')
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
