"""Celery task modules (auto-discovered).

Scheduled notification tasks use the same async session factory as the API.
"""

import asyncio

from sqlalchemy import distinct, select

from app.workers.celery_app import celery_app


@celery_app.task(name="health.echo")
def echo(value: str) -> str:
    """Sanity task proving the worker + broker wiring works."""
    return f"ok:{value}"


async def _dispatch_scheduled_notifications() -> int:
    from app.db.session import async_session_factory
    from app.services.notifications import NotificationService

    async with async_session_factory() as db:
        return await NotificationService(db).dispatch_scheduled()


@celery_app.task(
    name="notifications.dispatch_scheduled",
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
def dispatch_scheduled_notifications() -> int:
    """Deliver scheduled notifications that are due, once."""
    return asyncio.run(_dispatch_scheduled_notifications())


async def _create_calendar_reminders() -> int:
    from app.db.session import async_session_factory
    from app.models.calendar import CropSchedule
    from app.services.notification_triggers import NotificationTriggerService

    async with async_session_factory() as db:
        schedules = await db.execute(select(CropSchedule.user_id, CropSchedule.id))
        total = 0
        for user_id, schedule_id in schedules:
            created = await NotificationTriggerService(db).maybe_notify_task_reminder(
                user_id, schedule_id
            )
            total += len(created)
        return total


@celery_app.task(name="notifications.create_calendar_reminders")
def create_calendar_reminders() -> int:
    """Create notifications for users' upcoming, incomplete calendar tasks."""
    return asyncio.run(_create_calendar_reminders())


async def _create_treatment_reminders() -> int:
    from app.db.session import async_session_factory
    from app.models.recovery import RecoveryLog
    from app.models.scan import Scan
    from app.services.notification_triggers import NotificationTriggerService

    async with async_session_factory() as db:
        scans = await db.execute(
            select(distinct(Scan.user_id), Scan.id)
            .join(RecoveryLog, RecoveryLog.scan_id == Scan.id)
            .where(Scan.deleted_at.is_(None))
        )
        total = 0
        for user_id, scan_id in scans:
            if await NotificationTriggerService(db).maybe_notify_treatment_reminder(
                user_id, scan_id
            ):
                total += 1
        return total


@celery_app.task(name="notifications.create_treatment_reminders")
def create_treatment_reminders() -> int:
    """Create due treatment follow-up reminders from recorded recovery logs."""
    return asyncio.run(_create_treatment_reminders())
