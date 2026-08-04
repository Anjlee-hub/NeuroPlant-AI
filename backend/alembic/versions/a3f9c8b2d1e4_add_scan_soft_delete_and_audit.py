"""add scan soft-delete column and audit_logs table (Task 4.3)

Revision ID: a3f9c8b2d1e4
Revises: 5c9a2e7f41b0
Create Date: 2026-08-04 15:00:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = 'a3f9c8b2d1e4'
down_revision: str | None = '5c9a2e7f41b0'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Soft-delete marker on scans (NULL = live).
    op.add_column('scans', sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True))
    op.create_index(
        op.f('ix_scans_user_deleted_created'),
        'scans',
        ['user_id', 'deleted_at', 'created_at'],
        unique=False,
    )

    # Append-only audit trail (destructive actions).
    op.create_table(
        'audit_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('actor_id', sa.Integer(), nullable=True),
        sa.Column('action', sa.String(length=64), nullable=False),
        sa.Column('resource_type', sa.String(length=32), nullable=False),
        sa.Column('resource_id', sa.String(length=64), nullable=False),
        sa.Column('details', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.ForeignKeyConstraint(['actor_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_audit_logs_actor_id'), 'audit_logs', ['actor_id'], unique=False)
    op.create_index(
        op.f('ix_audit_logs_actor_created'), 'audit_logs', ['actor_id', 'created_at'], unique=False
    )
    op.create_index(
        op.f('ix_audit_logs_resource'), 'audit_logs', ['resource_type', 'resource_id'], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f('ix_audit_logs_resource'), table_name='audit_logs')
    op.drop_index(op.f('ix_audit_logs_actor_created'), table_name='audit_logs')
    op.drop_index(op.f('ix_audit_logs_actor_id'), table_name='audit_logs')
    op.drop_table('audit_logs')
    op.drop_index(op.f('ix_scans_user_deleted_created'), table_name='scans')
    op.drop_column('scans', 'deleted_at')
