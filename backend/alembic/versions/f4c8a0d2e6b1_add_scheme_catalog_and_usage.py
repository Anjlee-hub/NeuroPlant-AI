"""add government scheme catalog and usage events

Revision ID: f4c8a0d2e6b1
Revises: f3b7d9e1a2c4
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "f4c8a0d2e6b1"
down_revision: str | None = "f3b7d9e1a2c4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "government_schemes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("category", sa.String(80), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("benefits", sa.Text(), nullable=True),
        sa.Column("state_codes", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("crops", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column(
            "farmer_categories", sa.JSON(), nullable=False, server_default=sa.text("'[]'")
        ),
        sa.Column(
            "eligibility_requirements", sa.JSON(), nullable=False, server_default=sa.text("'[]'")
        ),
        sa.Column(
            "eligibility_rules", sa.JSON(), nullable=False, server_default=sa.text("'{}'")
        ),
        sa.Column(
            "required_documents", sa.JSON(), nullable=False, server_default=sa.text("'[]'")
        ),
        sa.Column("application_instructions", sa.Text(), nullable=True),
        sa.Column("official_application_url", sa.String(1000), nullable=True),
        sa.Column("subsidy_details", sa.Text(), nullable=True),
        sa.Column("source_name", sa.String(200), nullable=False),
        sa.Column("source_url", sa.String(1000), nullable=False),
        sa.Column("last_verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_verified", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_government_schemes_name", "government_schemes", ["name"])
    op.create_index("ix_government_schemes_category", "government_schemes", ["category"])
    op.create_index(
        "ix_government_schemes_active_verified",
        "government_schemes",
        ["is_active", "is_verified"],
    )
    op.create_table(
        "scheme_usage_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "scheme_id",
            sa.Integer(),
            sa.ForeignKey("government_schemes.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("action", sa.String(30), nullable=False),
        sa.Column("state_code", sa.String(8), nullable=True),
        sa.Column("crop_name", sa.String(120), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_scheme_usage_events_user_id", "scheme_usage_events", ["user_id"])
    op.create_index("ix_scheme_usage_events_scheme_id", "scheme_usage_events", ["scheme_id"])
    op.create_index(
        "ix_scheme_usage_user_created", "scheme_usage_events", ["user_id", "created_at"]
    )
    op.create_index(
        "ix_scheme_usage_scheme_action", "scheme_usage_events", ["scheme_id", "action"]
    )


def downgrade() -> None:
    op.drop_index("ix_scheme_usage_scheme_action", table_name="scheme_usage_events")
    op.drop_index("ix_scheme_usage_user_created", table_name="scheme_usage_events")
    op.drop_index("ix_scheme_usage_events_scheme_id", table_name="scheme_usage_events")
    op.drop_index("ix_scheme_usage_events_user_id", table_name="scheme_usage_events")
    op.drop_table("scheme_usage_events")
    op.drop_index("ix_government_schemes_active_verified", table_name="government_schemes")
    op.drop_index("ix_government_schemes_category", table_name="government_schemes")
    op.drop_index("ix_government_schemes_name", table_name="government_schemes")
    op.drop_table("government_schemes")
