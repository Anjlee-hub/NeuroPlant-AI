"""Structured logging via structlog.

Console-friendly pretty logging in development, JSON lines in production so the
deployment platform (Railway/Render) and log aggregators can ingest it cleanly.
"""

import logging
import sys

import structlog

from app.core.config import get_settings


def configure_logging() -> None:
    settings = get_settings()
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=logging.DEBUG if settings.debug else logging.INFO,
    )

    shared_processors: list[structlog.typing.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    if settings.is_production:
        # Machine-readable JSON for log pipelines.
        processors = shared_processors + [structlog.processors.JSONRenderer()]
    else:
        # Colored, human-readable console output.
        processors = shared_processors + [
            structlog.dev.ConsoleRenderer(colors=True, sort_keys=True)
        ]

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(
            logging.INFO if not settings.debug else logging.DEBUG
        ),
        cache_logger_on_first_use=True,
    )

    # Route standard-library loggers (uvicorn, sqlalchemy) through structlog.
    logging.getLogger("uvicorn.access").handlers = []
    for name in ("uvicorn", "uvicorn.error", "sqlalchemy.engine"):
        logging.getLogger(name).handlers = [logging.StreamHandler(sys.stdout)]


def get_logger(name: str = "neuroplant") -> structlog.stdlib.BoundLogger:
    return structlog.get_logger(name)
