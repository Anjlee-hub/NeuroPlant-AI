"""add marketplace tables (M4, Task 1)

Revision ID: a1c3e5b7d9f2
Revises: f5a7c9e1b3d5
Create Date: 2026-08-07 09:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = 'a1c3e5b7d9f2'
down_revision: str | None = 'f5a7c9e1b3d5'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Farmer produce listings — the marketplace's browse/search surface.
    op.create_table(
        'crop_listings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('farmer_id', sa.Integer(), nullable=False),
        sa.Column('crop_name', sa.String(length=120), nullable=False),
        sa.Column('category', sa.String(length=40), nullable=False),
        sa.Column('variety', sa.String(length=120), nullable=True),
        sa.Column('quantity', sa.Float(), nullable=False),
        sa.Column('unit', sa.String(length=20), nullable=False),
        sa.Column('price', sa.Float(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('images', sa.JSON(), nullable=True),
        sa.Column('harvest_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('organic', sa.Boolean(), nullable=False),
        sa.Column('location', sa.String(length=200), nullable=True),
        sa.Column('availability', sa.String(length=20), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.ForeignKeyConstraint(['farmer_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_crop_listings_availability'), 'crop_listings', ['availability'], unique=False)
    op.create_index(op.f('ix_crop_listings_category'), 'crop_listings', ['category'], unique=False)
    op.create_index(op.f('ix_crop_listings_farmer_id'), 'crop_listings', ['farmer_id'], unique=False)

    # Seller product catalog (fertilizer | pesticide | seed | tool).
    op.create_table(
        'products',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('seller_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('category', sa.String(length=30), nullable=False),
        sa.Column('brand', sa.String(length=120), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('price', sa.Float(), nullable=False),
        sa.Column('unit', sa.String(length=20), nullable=False),
        sa.Column('stock_quantity', sa.Float(), nullable=True),
        sa.Column('images', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.ForeignKeyConstraint(['seller_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_products_seller_id'), 'products', ['seller_id'], unique=False)

    # SellerProfile doubles as the marketplace Seller model (M4, Task 1) —
    # add the requirement's missing fields. Delivery/rating use a server
    # default so the NOT NULL columns stay compatible with SQLite ALTER ADD
    # COLUMN (which requires a default for NOT NULL additions).
    op.add_column('seller_profiles', sa.Column('phone', sa.String(length=20), nullable=True))
    op.add_column(
        'seller_profiles',
        sa.Column('delivery_available', sa.Boolean(), server_default=sa.text('0'), nullable=False),
    )
    op.add_column(
        'seller_profiles',
        sa.Column('rating', sa.Float(), server_default=sa.text('0'), nullable=False),
    )


def downgrade() -> None:
    op.drop_column('seller_profiles', 'rating')
    op.drop_column('seller_profiles', 'delivery_available')
    op.drop_column('seller_profiles', 'phone')
    op.drop_index(op.f('ix_products_seller_id'), table_name='products')
    op.drop_table('products')
    op.drop_index(op.f('ix_crop_listings_farmer_id'), table_name='crop_listings')
    op.drop_index(op.f('ix_crop_listings_category'), table_name='crop_listings')
    op.drop_index(op.f('ix_crop_listings_availability'), table_name='crop_listings')
    op.drop_table('crop_listings')
