"""Async SQLAlchemy engine + session factory.

Works with PostgreSQL (asyncpg) in production and SQLite (aiosqlite) in
native dev mode. SQLite has no native JSONB or enum types, so models must use
portable types (String, JSON, Integer) — the Alembic migration for Postgres
can still emit Postgres-specific constructs via server_defaults/spiegelungen.
"""

from collections.abc import AsyncGenerator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.core.config import get_settings


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""


def _make_engine():
    settings = get_settings()
    kwargs: dict = {"echo": settings.db_echo, "future": True}
    if settings.database_url.startswith("sqlite"):
        # SQLite requires check_same_thread disabled for async usage.
        kwargs["connect_args"] = {"check_same_thread": False}
    return create_async_engine(settings.database_url, **kwargs)


engine = _make_engine()

async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency yielding a database session."""
    async with async_session_factory() as session:
        yield session


async def ping_db() -> bool:
    """Cheap reachability check used by the /ready probe."""
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception:  # noqa: BLE001 — a probe must never raise
        return False
