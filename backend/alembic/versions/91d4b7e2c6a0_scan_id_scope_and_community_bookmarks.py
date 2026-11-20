"""Add persistent community bookmarks.

Revision ID: 91d4b7e2c6a0
Revises: 4b1373ad24cd
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "91d4b7e2c6a0"
down_revision: str | None = "4b1373ad24cd"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "community_bookmarks",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("post_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["post_id"], ["community_posts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("post_id", "user_id", name="uq_community_bookmark"),
    )
    op.create_index("ix_community_bookmarks_post_id", "community_bookmarks", ["post_id"])
    op.create_index("ix_community_bookmarks_user_id", "community_bookmarks", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_community_bookmarks_user_id", table_name="community_bookmarks")
    op.drop_index("ix_community_bookmarks_post_id", table_name="community_bookmarks")
    op.drop_table("community_bookmarks")
