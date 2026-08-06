"""add crop calendar tables (M3, Task 5)

Revision ID: e4f6a8b0c2d1
Revises: d9e7f5b3c1a2
Create Date: 2026-08-06 15:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = 'e4f6a8b0c2d1'
down_revision: str | None = 'd9e7f5b3c1a2'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Versioned growth-stage catalog (exactly one active — the M3 catalog pattern).
    op.create_table(
        'crop_calendar_catalogs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('version', sa.String(length=32), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        op.f('ix_crop_calendar_catalogs_version'),
        'crop_calendar_catalogs',
        ['version'],
        unique=True,
    )

    # One growth-stage template per (catalog, crop).
    op.create_table(
        'crop_calendar_plans',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('catalog_id', sa.Integer(), nullable=False),
        sa.Column('crop_id', sa.Integer(), nullable=False),
        sa.Column('planting_start_month', sa.Integer(), nullable=False),
        sa.Column('planting_end_month', sa.Integer(), nullable=False),
        sa.Column('germination_days', sa.Integer(), nullable=False),
        sa.Column('vegetative_days', sa.Integer(), nullable=False),
        sa.Column('flowering_days', sa.Integer(), nullable=False),
        sa.Column('fruiting_days', sa.Integer(), nullable=False),
        sa.Column('harvest_days', sa.Integer(), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.ForeignKeyConstraint(['catalog_id'], ['crop_calendar_catalogs.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['crop_id'], ['crops.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('catalog_id', 'crop_id', name='uq_crop_calendar_crop'),
    )
    op.create_index(
        op.f('ix_crop_calendar_plans_catalog_id'),
        'crop_calendar_plans',
        ['catalog_id'],
        unique=False,
    )
    op.create_index(
        op.f('ix_crop_calendar_plans_crop_id'),
        'crop_calendar_plans',
        ['crop_id'],
        unique=False,
    )

    # One active schedule per (user, crop), anchored to a planting date.
    op.create_table(
        'crop_schedules',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('crop_id', sa.Integer(), nullable=False),
        sa.Column('planting_date', sa.Date(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.ForeignKeyConstraint(['crop_id'], ['crops.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'crop_id', name='uq_crop_schedule_user_crop'),
    )
    op.create_index(
        op.f('ix_crop_schedules_user_id'),
        'crop_schedules',
        ['user_id'],
        unique=False,
    )
    op.create_index(
        op.f('ix_crop_schedules_crop_id'),
        'crop_schedules',
        ['crop_id'],
        unique=False,
    )

    # Concrete reminder tasks (watering / fertilizer / treatment / monitoring /
    # soil inspection / custom). scan_id links disease reminders to their scan.
    op.create_table(
        'calendar_tasks',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('schedule_id', sa.Integer(), nullable=False),
        sa.Column('scan_id', sa.Integer(), nullable=True),
        sa.Column('kind', sa.String(length=30), nullable=False),
        sa.Column('title', sa.String(length=300), nullable=False),
        sa.Column('due_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('snooze_count', sa.Integer(), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.ForeignKeyConstraint(['scan_id'], ['scans.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['schedule_id'], ['crop_schedules.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        op.f('ix_calendar_tasks_schedule_id'),
        'calendar_tasks',
        ['schedule_id'],
        unique=False,
    )
    op.create_index(
        op.f('ix_calendar_tasks_scan_id'),
        'calendar_tasks',
        ['scan_id'],
        unique=False,
    )
    op.create_index(
        op.f('ix_calendar_tasks_kind'),
        'calendar_tasks',
        ['kind'],
        unique=False,
    )
    op.create_index(
        op.f('ix_calendar_tasks_due_at'),
        'calendar_tasks',
        ['due_at'],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f('ix_calendar_tasks_due_at'), table_name='calendar_tasks')
    op.drop_index(op.f('ix_calendar_tasks_kind'), table_name='calendar_tasks')
    op.drop_index(op.f('ix_calendar_tasks_scan_id'), table_name='calendar_tasks')
    op.drop_index(op.f('ix_calendar_tasks_schedule_id'), table_name='calendar_tasks')
    op.drop_table('calendar_tasks')
    op.drop_index(op.f('ix_crop_schedules_crop_id'), table_name='crop_schedules')
    op.drop_index(op.f('ix_crop_schedules_user_id'), table_name='crop_schedules')
    op.drop_table('crop_schedules')
    op.drop_index(op.f('ix_crop_calendar_plans_crop_id'), table_name='crop_calendar_plans')
    op.drop_index(op.f('ix_crop_calendar_plans_catalog_id'), table_name='crop_calendar_plans')
    op.drop_table('crop_calendar_plans')
    op.drop_index(op.f('ix_crop_calendar_catalogs_version'), table_name='crop_calendar_catalogs')
    op.drop_table('crop_calendar_catalogs')
