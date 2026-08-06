"""add soil recommendation catalog + soil recommendation tables (M3, Task 3)

Revision ID: c5e1f3a7b9d2
Revises: b4d2e6f8a1c3
Create Date: 2026-08-06 09:30:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = 'c5e1f3a7b9d2'
down_revision: str | None = 'b4d2e6f8a1c3'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Versioned soil-intelligence knowledge base: exactly one catalog is active.
    op.create_table(
        'soil_recommendation_catalogs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('version', sa.String(length=32), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        op.f('ix_soil_recommendation_catalogs_version'),
        'soil_recommendation_catalogs',
        ['version'],
        unique=True,
    )

    # One complete soil plan per (catalog, disease); repeatable lists + the
    # severity-aware dicts are JSON.
    op.create_table(
        'soil_recommendations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('catalog_id', sa.Integer(), nullable=False),
        sa.Column('disease_id', sa.Integer(), nullable=False),
        sa.Column('recommended_soil_type', sa.Text(), nullable=True),
        sa.Column('ph_range', sa.String(length=40), nullable=True),
        sa.Column('moisture_level', sa.Text(), nullable=True),
        sa.Column('drainage', sa.Text(), nullable=True),
        sa.Column('organic_matter', sa.Text(), nullable=True),
        sa.Column('npk', sa.Text(), nullable=True),
        sa.Column('micronutrients', sa.JSON(), nullable=True),
        sa.Column('compost', sa.Text(), nullable=True),
        sa.Column('mulching', sa.Text(), nullable=True),
        sa.Column('soil_suitability', sa.Text(), nullable=True),
        sa.Column('base_soil_health', sa.String(length=20), nullable=True),
        sa.Column('improvement_suggestions', sa.JSON(), nullable=True),
        sa.Column('disease_soil_notes', sa.Text(), nullable=True),
        sa.Column('severity_notes', sa.JSON(), nullable=True),
        sa.Column('severity_suggestions', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.ForeignKeyConstraint(['catalog_id'], ['soil_recommendation_catalogs.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['disease_id'], ['diseases.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('catalog_id', 'disease_id', name='uq_soil_catalog_disease'),
    )
    op.create_index(
        op.f('ix_soil_recommendations_catalog_id'),
        'soil_recommendations',
        ['catalog_id'],
        unique=False,
    )
    op.create_index(
        op.f('ix_soil_recommendations_disease_id'),
        'soil_recommendations',
        ['disease_id'],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f('ix_soil_recommendations_disease_id'), table_name='soil_recommendations')
    op.drop_index(op.f('ix_soil_recommendations_catalog_id'), table_name='soil_recommendations')
    op.drop_table('soil_recommendations')
    op.drop_index(op.f('ix_soil_recommendation_catalogs_version'), table_name='soil_recommendation_catalogs')
    op.drop_table('soil_recommendation_catalogs')
