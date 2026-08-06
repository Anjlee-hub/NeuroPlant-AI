"""add conversation_messages table (M3.1)

Revision ID: f5a7c9e1b3d5
Revises: e4f6a8b0c2d1
Create Date: 2026-08-06 18:30:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = 'f5a7c9e1b3d5'
down_revision: str | None = 'e4f6a8b0c2d1'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Per-user rolling transcript powering conversational follow-ups (M3.1).
    op.create_table(
        'conversation_messages',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('role', sa.String(length=16), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('intent', sa.String(length=40), nullable=True),
        sa.Column('lang', sa.String(length=8), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        op.f('ix_conversation_messages_user_id'),
        'conversation_messages',
        ['user_id'],
        unique=False,
    )
    op.create_index(
        op.f('ix_conversation_messages_created_at'),
        'conversation_messages',
        ['created_at'],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f('ix_conversation_messages_created_at'), table_name='conversation_messages')
    op.drop_index(op.f('ix_conversation_messages_user_id'), table_name='conversation_messages')
    op.drop_table('conversation_messages')
