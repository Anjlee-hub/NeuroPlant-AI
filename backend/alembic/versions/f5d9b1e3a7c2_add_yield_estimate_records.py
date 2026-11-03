"""add persisted yield estimates for analytics

Revision ID: f5d9b1e3a7c2
Revises: f4c8a0d2e6b1
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "f5d9b1e3a7c2"
down_revision: str | None = "f4c8a0d2e6b1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "yield_estimate_records",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "crop_id",
            sa.Integer(),
            sa.ForeignKey("crops.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "schedule_id",
            sa.Integer(),
            sa.ForeignKey("crop_schedules.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("planting_date", sa.Date(), nullable=False),
        sa.Column("area_hectares", sa.Float(), nullable=False),
        sa.Column("estimated_yield_kg", sa.Float(), nullable=True),
        sa.Column("historical_harvest_count", sa.Integer(), nullable=False),
        sa.Column("reliability", sa.String(20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_yield_estimate_records_user_id", "yield_estimate_records", ["user_id"]
    )
    op.create_index(
        "ix_yield_estimate_records_crop_id", "yield_estimate_records", ["crop_id"]
    )
    op.create_index(
        "ix_yield_estimate_records_schedule_id", "yield_estimate_records", ["schedule_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_yield_estimate_records_schedule_id", table_name="yield_estimate_records")
    op.drop_index("ix_yield_estimate_records_crop_id", table_name="yield_estimate_records")
    op.drop_index("ix_yield_estimate_records_user_id", table_name="yield_estimate_records")
    op.drop_table("yield_estimate_records")
