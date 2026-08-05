"""add recommendation catalog + disease recommendation tables (M3, Task 1)

Revision ID: b4d2e6f8a1c3
Revises: a3f9c8b2d1e4
Create Date: 2026-08-05 21:00:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = 'b4d2e6f8a1c3'
down_revision: str | None = 'a3f9c8b2d1e4'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Versioned treatment knowledge base: exactly one catalog is active at a time.
    op.create_table(
        'recommendation_catalogs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('version', sa.String(length=32), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        op.f('ix_recommendation_catalogs_version'),
        'recommendation_catalogs',
        ['version'],
        unique=True,
    )

    # One complete plan per (catalog, disease); repeatable lists are JSON.
    op.create_table(
        'disease_recommendations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('catalog_id', sa.Integer(), nullable=False),
        sa.Column('disease_id', sa.Integer(), nullable=False),
        sa.Column('overview', sa.Text(), nullable=True),
        sa.Column('cause', sa.Text(), nullable=True),
        sa.Column('symptoms', sa.JSON(), nullable=True),
        sa.Column('severity', sa.String(length=40), nullable=True),
        sa.Column('spread_mechanism', sa.Text(), nullable=True),
        sa.Column('homemade_remedies', sa.JSON(), nullable=True),
        sa.Column('organic_remedies', sa.JSON(), nullable=True),
        sa.Column('chemical_recommendations', sa.JSON(), nullable=True),
        sa.Column('fertilizer', sa.Text(), nullable=True),
        sa.Column('watering', sa.Text(), nullable=True),
        sa.Column('sunlight', sa.Text(), nullable=True),
        sa.Column('temperature', sa.Text(), nullable=True),
        sa.Column('humidity', sa.Text(), nullable=True),
        sa.Column('prevention_tips', sa.JSON(), nullable=True),
        sa.Column('recovery_timeline', sa.Text(), nullable=True),
        sa.Column('isolation', sa.Text(), nullable=True),
        sa.Column('monitoring_advice', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.ForeignKeyConstraint(['catalog_id'], ['recommendation_catalogs.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['disease_id'], ['diseases.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('catalog_id', 'disease_id', name='uq_recommendation_catalog_disease'),
    )
    op.create_index(
        op.f('ix_disease_recommendations_catalog_id'),
        'disease_recommendations',
        ['catalog_id'],
        unique=False,
    )
    op.create_index(
        op.f('ix_disease_recommendations_disease_id'),
        'disease_recommendations',
        ['disease_id'],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f('ix_disease_recommendations_disease_id'), table_name='disease_recommendations')
    op.drop_index(op.f('ix_disease_recommendations_catalog_id'), table_name='disease_recommendations')
    op.drop_table('disease_recommendations')
    op.drop_index(op.f('ix_recommendation_catalogs_version'), table_name='recommendation_catalogs')
    op.drop_table('recommendation_catalogs')
