"""add scheme catalogue metadata and saved schemes

Revision ID: c7d1e3f5a9b2
Revises: f6a2c8e0b1d3
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "c7d1e3f5a9b2"
down_revision: str | None = "f6a2c8e0b1d3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "government_schemes",
        sa.Column("department", sa.String(200), nullable=False, server_default="Official department"),
    )
    op.add_column(
        "government_schemes",
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
    )
    op.add_column(
        "government_schemes",
        sa.Column("district_codes", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
    )
    op.create_index("ix_government_schemes_status", "government_schemes", ["status"])
    op.create_index("uq_government_schemes_name", "government_schemes", ["name"], unique=True)
    op.create_index(
        "uq_government_schemes_source_url",
        "government_schemes",
        ["source_url"],
        unique=True,
    )
    op.create_table(
        "saved_government_schemes",
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
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("user_id", "scheme_id", name="uq_saved_government_scheme"),
    )
    op.create_index(
        "ix_saved_government_schemes_user_id",
        "saved_government_schemes",
        ["user_id"],
    )
    op.create_index(
        "ix_saved_government_schemes_scheme_id",
        "saved_government_schemes",
        ["scheme_id"],
    )
    op.create_index(
        "ix_saved_government_schemes_user_scheme",
        "saved_government_schemes",
        ["user_id", "scheme_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_saved_government_schemes_user_scheme",
        table_name="saved_government_schemes",
    )
    op.drop_index(
        "ix_saved_government_schemes_scheme_id",
        table_name="saved_government_schemes",
    )
    op.drop_index(
        "ix_saved_government_schemes_user_id",
        table_name="saved_government_schemes",
    )
    op.drop_table("saved_government_schemes")
    op.drop_index("uq_government_schemes_source_url", table_name="government_schemes")
    op.drop_index("uq_government_schemes_name", table_name="government_schemes")
    op.drop_index("ix_government_schemes_status", table_name="government_schemes")
    op.drop_column("government_schemes", "district_codes")
    op.drop_column("government_schemes", "status")
    op.drop_column("government_schemes", "department")
