"""add recovery_logs table (M3, Task 4)

Revision ID: d9e7f5b3c1a2
Revises: c5e1f3a7b9d2
Create Date: 2026-08-06 14:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = 'd9e7f5b3c1a2'
down_revision: str | None = 'c5e1f3a7b9d2'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # One row per treatment action a farmer logs against a diagnosed scan.
    # user_id is denormalized (from the scan) for direct ownership filtering.
    op.create_table(
        'recovery_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('scan_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('treatment_applied', sa.String(length=500), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('progress', sa.String(length=20), nullable=True),
        sa.Column('applied_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.ForeignKeyConstraint(['scan_id'], ['scans.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        op.f('ix_recovery_logs_scan_id'),
        'recovery_logs',
        ['scan_id'],
        unique=False,
    )
    op.create_index(
        op.f('ix_recovery_logs_user_id'),
        'recovery_logs',
        ['user_id'],
        unique=False,
    )
    op.create_index(
        op.f('ix_recovery_logs_scan_applied'),
        'recovery_logs',
        ['scan_id', 'applied_at'],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f('ix_recovery_logs_scan_applied'), table_name='recovery_logs')
    op.drop_index(op.f('ix_recovery_logs_user_id'), table_name='recovery_logs')
    op.drop_index(op.f('ix_recovery_logs_scan_id'), table_name='recovery_logs')
    op.drop_table('recovery_logs')
