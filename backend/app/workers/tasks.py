"""Celery task modules (auto-discovered).

Placeholder for M0. Real task families arrive per milestone:

M2  ``detect_image``        — AI disease inference (+ cloud fallback)
M3  ``generate_health_pdf`` — Crop Doctor weekly report (ReportLab)
M4  ``ingest_approved_sample`` — dataset-platform label → retrain trigger
M5  ``notify_*`` / ``refresh_weather`` — scheduled jobs via Celery beat
"""

from app.workers.celery_app import celery_app


@celery_app.task(name="health.echo")
def echo(value: str) -> str:
    """Sanity task proving the worker + broker wiring works."""
    return f"ok:{value}"
