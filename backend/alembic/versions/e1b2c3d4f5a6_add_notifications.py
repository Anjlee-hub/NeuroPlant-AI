"""add notifications table (M5, Task 2)

Revision ID: e1b2c3d4f5a6
Revises: d2f4a6c8e0b1
Create Date: 2026-08-12 14:20:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# Stable notification type enum — shared with ``app.models.notification``.
NOTIFICATION_TYPES = (
    "weather_risk",
    "disease_risk",
    "treatment_reminder",
    "task_reminder",
    "outbreak_alert",
    "yield_prediction",
    "price_alert",
    "marketplace_message",
    "review_received",
    "order_update",
    "system",
)


revision: str = 'e1b2c3d4f5a6'
down_revision: str | None = 'd2f4a6c8e0b1'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # On Postgres, create a real enum type; SQLite has no enum support, so the
    # column is a plain VARCHAR with the values enforced by the app layer.
    if op.get_bind().dialect.name == "postgresql":
        sa.Enum(*NOTIFICATION_TYPES, name="notification_type").create(
            op.get_bind(), checkfirst=True
        )
        type_col = sa.Column(
            "type",
            postgresql.ENUM(*NOTIFICATION_TYPES, name="notification_type"),
            nullable=False,
        )
    else:
        type_col = sa.Column("type", sa.String(32), nullable=False)

    op.create_table(
        "notifications",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        type_col,
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("payload", sa.JSON().with_variant(sa.Text(), "sqlite"), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_notifications_user_unread", "notifications", ["user_id", "read_at"])
    op.create_index(
        "ix_notifications_user_scheduled", "notifications", ["user_id", "scheduled_at"]
    )
    op.create_index(
        "ix_notifications_user_created", "notifications", ["user_id", "created_at"]
    )
    op.create_index("ix_notifications_type", "notifications", ["type"])


def downgrade() -> None:
    op.drop_index("ix_notifications_type", table_name="notifications")
    op.drop_index("ix_notifications_user_created", table_name="notifications")
    op.drop_index("ix_notifications_user_scheduled", table_name="notifications")
    op.drop_index("ix_notifications_user_unread", table_name="notifications")
    op.drop_table("notifications")
    if op.get_bind().dialect.name == "postgresql":
        sa.Enum(name="notification_type").drop(op.get_bind(), checkfirst=True)
