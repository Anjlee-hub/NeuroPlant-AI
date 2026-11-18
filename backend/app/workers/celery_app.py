"""Celery application instance.

Native dev runs with ``task_always_eager`` (no broker required). In
production the broker/backend are Redis URLs supplied via environment.
"""

from celery import Celery

from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "neuroplant",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

celery_app.conf.update(
    task_always_eager=settings.celery_task_always_eager,
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    result_expires=60 * 60 * 24,  # 24h
    timezone="UTC",
    enable_utc=True,
    broker_connection_retry_on_startup=True,
    include=["app.workers.tasks"],
)

celery_app.conf.beat_schedule = {
    "dispatch-scheduled-notifications-every-minute": {
        "task": "notifications.dispatch_scheduled",
        "schedule": 60.0,
    },
    "create-calendar-reminders-every-15-minutes": {
        "task": "notifications.create_calendar_reminders",
        "schedule": 15 * 60.0,
    },
    "create-treatment-reminders-hourly": {
        "task": "notifications.create_treatment_reminders",
        "schedule": 60 * 60.0,
    },
}
