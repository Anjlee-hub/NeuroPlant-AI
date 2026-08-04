"""add scans table (M2 disease detection)

Revision ID: 5c9a2e7f41b0
Revises: e7a4341cf99e
Create Date: 2026-08-04 12:30:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = '5c9a2e7f41b0'
down_revision: str | None = 'e7a4341cf99e'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table('scans',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('client_scan_id', sa.String(length=36), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('media_items', sa.JSON(), nullable=False),
    sa.Column('image_path', sa.String(length=500), nullable=False),
    sa.Column('processed_image_path', sa.String(length=500), nullable=True),
    sa.Column('heatmap_path', sa.String(length=500), nullable=True),
    sa.Column('crop_id', sa.Integer(), nullable=True),
    sa.Column('part_type', sa.String(length=20), nullable=True),
    sa.Column('disease_id', sa.Integer(), nullable=True),
    sa.Column('disease_name', sa.String(length=160), nullable=False),
    sa.Column('confidence', sa.Float(), nullable=False),
    sa.Column('severity', sa.String(length=20), nullable=True),
    sa.Column('stage', sa.String(length=60), nullable=True),
    sa.Column('provider', sa.String(length=40), nullable=False),
    sa.Column('model_name', sa.String(length=120), nullable=True),
    sa.Column('model_version', sa.String(length=60), nullable=True),
    sa.Column('dataset_version', sa.String(length=40), nullable=True),
    sa.Column('preprocessing_time_ms', sa.Float(), nullable=False),
    sa.Column('inference_time_ms', sa.Float(), nullable=False),
    sa.Column('processing_time_ms', sa.Float(), nullable=False),
    sa.Column('ai_metadata', sa.JSON(), nullable=True),
    sa.Column('sync_status', sa.String(length=20), nullable=False),
    sa.Column('sync_error', sa.String(length=500), nullable=True),
    sa.Column('device_id', sa.String(length=64), nullable=True),
    sa.Column('synced_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.ForeignKeyConstraint(['crop_id'], ['crops.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['disease_id'], ['diseases.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_scans_client_scan_id'), 'scans', ['client_scan_id'], unique=True)
    op.create_index(op.f('ix_scans_crop_id'), 'scans', ['crop_id'], unique=False)
    op.create_index(op.f('ix_scans_disease_id'), 'scans', ['disease_id'], unique=False)
    op.create_index(op.f('ix_scans_disease_name'), 'scans', ['disease_name'], unique=False)
    op.create_index(op.f('ix_scans_user_created'), 'scans', ['user_id', 'created_at'], unique=False)
    op.create_index(op.f('ix_scans_user_id'), 'scans', ['user_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_scans_user_id'), table_name='scans')
    op.drop_index(op.f('ix_scans_user_created'), table_name='scans')
    op.drop_index(op.f('ix_scans_disease_name'), table_name='scans')
    op.drop_index(op.f('ix_scans_disease_id'), table_name='scans')
    op.drop_index(op.f('ix_scans_crop_id'), table_name='scans')
    op.drop_index(op.f('ix_scans_client_scan_id'), table_name='scans')
    op.drop_table('scans')
