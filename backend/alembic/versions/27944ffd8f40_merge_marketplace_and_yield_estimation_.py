"""merge marketplace and yield estimation heads

Revision ID: 27944ffd8f40
Revises: 62368e719355, f5d9b1e3a7c2
Create Date: 2026-11-05 11:22:43.001310
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = '27944ffd8f40'
down_revision: str | None = ('62368e719355', 'f5d9b1e3a7c2')
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
