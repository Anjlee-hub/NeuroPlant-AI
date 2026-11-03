"""add notification idempotency key

Revision ID: f2a6c8e0b1d3
Revises: e1b2c3d4f5a6
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "f2a6c8e0b1d3"
down_revision: str | None = "e1b2c3d4f5a6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "notifications",
        sa.Column("idempotency_key", sa.String(length=200), nullable=True),
    )
    op.create_index(
        "uq_notifications_idempotency_key",
        "notifications",
        ["idempotency_key"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("uq_notifications_idempotency_key", table_name="notifications")
    op.drop_column("notifications", "idempotency_key")
