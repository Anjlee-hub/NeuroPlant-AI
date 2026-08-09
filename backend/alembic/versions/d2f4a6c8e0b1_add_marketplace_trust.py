"""add marketplace trust tables (M4, Task 6)

Revision ID: d2f4a6c8e0b1
Revises: c2e4f6a8b0d2
Create Date: 2026-08-08 16:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = 'd2f4a6c8e0b1'
down_revision: str | None = 'c2e4f6a8b0d2'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Saved items (favourites): one row per user per saved listing/product.
    # The listing/product references CASCADE — a saved copy dies with the item
    # (a favourite of a deleted item is meaningless). A CHECK enforces exactly
    # one target context; two unique constraints (one per target kind) make
    # repeated saves impossible, which SQLite's NULL-distinct unique semantics
    # handle because exactly one target column is ever non-NULL.
    op.create_table(
        'marketplace_favorites',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('listing_id', sa.Integer(), sa.ForeignKey('crop_listings.id', ondelete='CASCADE'), nullable=True),
        sa.Column('product_id', sa.Integer(), sa.ForeignKey('products.id', ondelete='CASCADE'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            '(listing_id IS NOT NULL AND product_id IS NULL)'
            ' OR (listing_id IS NULL AND product_id IS NOT NULL)',
            name='ck_marketplace_favorites_one_target',
        ),
        sa.UniqueConstraint('user_id', 'listing_id', name='uq_marketplace_favorites_listing'),
        sa.UniqueConstraint('user_id', 'product_id', name='uq_marketplace_favorites_product'),
    )
    op.create_index('ix_marketplace_favorites_user', 'marketplace_favorites', ['user_id'], unique=False)

    # Reviews/ratings: one review per reviewer per listing/product (unique
    # constraints, same NULL trick). seller_id is the review's subject (listing
    # farmer / product shop owner), denormalised for fast reputation queries.
    # The listing/product references SET NULL so review history (and the seller
    # reputation it feeds) survives the item being deleted; there is
    # deliberately NO exactly-one CHECK here — on a SET NULL the row would
    # legitimately hold two NULLs and the CHECK would abort the parent delete.
    op.create_table(
        'marketplace_reviews',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('reviewer_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('seller_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('listing_id', sa.Integer(), sa.ForeignKey('crop_listings.id', ondelete='SET NULL'), nullable=True),
        sa.Column('product_id', sa.Integer(), sa.ForeignKey('products.id', ondelete='SET NULL'), nullable=True),
        sa.Column('rating', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=200), nullable=True),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint('reviewer_id', 'listing_id', name='uq_marketplace_reviews_listing'),
        sa.UniqueConstraint('reviewer_id', 'product_id', name='uq_marketplace_reviews_product'),
    )
    op.create_index('ix_marketplace_reviews_reviewer', 'marketplace_reviews', ['reviewer_id'], unique=False)
    op.create_index('ix_marketplace_reviews_seller', 'marketplace_reviews', ['seller_id'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_marketplace_reviews_seller', table_name='marketplace_reviews')
    op.drop_index('ix_marketplace_reviews_reviewer', table_name='marketplace_reviews')
    op.drop_table('marketplace_reviews')
    op.drop_index('ix_marketplace_favorites_user', table_name='marketplace_favorites')
    op.drop_table('marketplace_favorites')
