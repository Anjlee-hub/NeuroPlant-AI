"""add marketplace messaging tables (M4, Task 5)

Revision ID: c2e4f6a8b0d2
Revises: b7d3f5a9c1e4
Create Date: 2026-08-08 14:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = 'c2e4f6a8b0d2'
down_revision: str | None = 'b7d3f5a9c1e4'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Buyer↔seller enquiry threads (M4 Task 5). The seller side is the shop
    # owner for products or the listing farmer for crops — both ``users.id``
    # rows. The listing/product reference is optional context and is nulled
    # (SET NULL) rather than cascaded when the referenced row is deleted, so a
    # retired listing never orphans the thread history.
    op.create_table(
        'marketplace_conversations',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('buyer_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('seller_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('listing_id', sa.Integer(), sa.ForeignKey('crop_listings.id', ondelete='SET NULL'), nullable=True),
        sa.Column('product_id', sa.Integer(), sa.ForeignKey('products.id', ondelete='SET NULL'), nullable=True),
        sa.Column('status', sa.String(length=20), server_default=sa.text("'active'"), nullable=False),
        sa.Column('last_message_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_marketplace_conversations_buyer', 'marketplace_conversations', ['buyer_id'], unique=False)
    op.create_index('ix_marketplace_conversations_seller', 'marketplace_conversations', ['seller_id'], unique=False)
    op.create_index('ix_marketplace_conversations_status', 'marketplace_conversations', ['status'], unique=False)

    # One turn per row: sender, text, and a NULL-until-read marker.
    op.create_table(
        'marketplace_messages',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('conversation_id', sa.Integer(), sa.ForeignKey('marketplace_conversations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('sender_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('read_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_marketplace_messages_conversation', 'marketplace_messages', ['conversation_id'], unique=False)
    op.create_index(
        'ix_marketplace_messages_conversation_created',
        'marketplace_messages',
        ['conversation_id', 'created_at'],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index('ix_marketplace_messages_conversation_created', table_name='marketplace_messages')
    op.drop_index('ix_marketplace_messages_conversation', table_name='marketplace_messages')
    op.drop_table('marketplace_messages')
    op.drop_index('ix_marketplace_conversations_status', table_name='marketplace_conversations')
    op.drop_index('ix_marketplace_conversations_seller', table_name='marketplace_conversations')
    op.drop_index('ix_marketplace_conversations_buyer', table_name='marketplace_conversations')
    op.drop_table('marketplace_conversations')
