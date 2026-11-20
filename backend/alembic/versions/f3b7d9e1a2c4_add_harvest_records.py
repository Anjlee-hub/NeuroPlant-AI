"""add farmer-recorded harvest records

Revision ID: f3b7d9e1a2c4
Revises: f2a6c8e0b1d3
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "f3b7d9e1a2c4"
down_revision: str | None = "f2a6c8e0b1d3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "harvest_records",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "schedule_id",
            sa.Integer(),
            sa.ForeignKey("crop_schedules.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("actual_yield_kg", sa.Float(), nullable=False),
        sa.Column("area_hectares", sa.Float(), nullable=False),
        sa.Column("harvested_on", sa.Date(), nullable=False),
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
        sa.CheckConstraint("actual_yield_kg > 0", name="ck_harvest_yield_positive"),
        sa.CheckConstraint("area_hectares > 0", name="ck_harvest_area_positive"),
    )
    op.create_index("ix_harvest_records_user_id", "harvest_records", ["user_id"])
    op.create_index("ix_harvest_records_schedule_id", "harvest_records", ["schedule_id"])
    op.create_index(
        "ix_harvest_user_schedule",
        "harvest_records",
        ["user_id", "schedule_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_harvest_user_schedule", table_name="harvest_records")
    op.drop_index("ix_harvest_records_schedule_id", table_name="harvest_records")
    op.drop_index("ix_harvest_records_user_id", table_name="harvest_records")
    op.drop_table("harvest_records")
