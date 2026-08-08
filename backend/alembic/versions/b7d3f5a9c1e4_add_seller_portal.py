"""add seller portal fields (M4, Task 4)

Revision ID: b7d3f5a9c1e4
Revises: a1c3e5b7d9f2
Create Date: 2026-08-07 15:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = 'b7d3f5a9c1e4'
down_revision: str | None = 'a1c3e5b7d9f2'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Product: the Seller Portal fields the Task 1 catalog lacked — an organic
    # badge, manufacturer, usage instructions, and a stock/archive lifecycle.
    # NOT NULL additions carry a server default so SQLite ALTER ADD COLUMN is
    # satisfied (same technique as the Task 1 delivery/rating columns).
    op.add_column('products', sa.Column('organic', sa.Boolean(), server_default=sa.text('0'), nullable=False))
    op.add_column('products', sa.Column('manufacturer', sa.String(length=200), nullable=True))
    op.add_column('products', sa.Column('usage_instructions', sa.Text(), nullable=True))
    op.add_column(
        'products',
        sa.Column('availability', sa.String(length=20), server_default=sa.text("'in_stock'"), nullable=False),
    )
    # Customers filter the public product market by category and availability.
    op.create_index(op.f('ix_products_category'), 'products', ['category'], unique=False)
    op.create_index(op.f('ix_products_availability'), 'products', ['availability'], unique=False)

    # Shop profile: description, opening hours, and media (logo/banner URLs).
    op.add_column('seller_profiles', sa.Column('description', sa.Text(), nullable=True))
    op.add_column('seller_profiles', sa.Column('opening_hours', sa.String(length=200), nullable=True))
    op.add_column('seller_profiles', sa.Column('logo_url', sa.String(length=500), nullable=True))
    op.add_column('seller_profiles', sa.Column('banner_url', sa.String(length=500), nullable=True))


def downgrade() -> None:
    op.drop_column('seller_profiles', 'banner_url')
    op.drop_column('seller_profiles', 'logo_url')
    op.drop_column('seller_profiles', 'opening_hours')
    op.drop_column('seller_profiles', 'description')
    op.drop_index(op.f('ix_products_availability'), table_name='products')
    op.drop_index(op.f('ix_products_category'), table_name='products')
    op.drop_column('products', 'availability')
    op.drop_column('products', 'usage_instructions')
    op.drop_column('products', 'manufacturer')
    op.drop_column('products', 'organic')
