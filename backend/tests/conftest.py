"""Test fixtures.

Environment must be configured *before* ``app`` is imported, because the
settings object and the async engine are created at import time.
"""

import os
import shutil
from pathlib import Path

os.environ.setdefault(
    "DATABASE_URL",
    "sqlite+aiosqlite:///./test-neuroplant.db",
)
os.environ.setdefault("ENVIRONMENT", "test")
# Surface OTP codes via the API so the flow is testable without SMS.
os.environ.setdefault("DEBUG", "true")
# Keep upload tests off the real ./storage dir (scrubbed before/after each test).
os.environ.setdefault("STORAGE_LOCAL_DIR", "./.test-storage")

import pytest_asyncio
from app.db.session import Base, async_session_factory, engine
from app.main import app  # noqa: F401  (import populates app + metadata)
from app.models import *  # noqa: F401,F403  (register every model on Base.metadata)
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

_STORAGE_DIR = Path(os.environ.get("STORAGE_LOCAL_DIR", "./.test-storage"))


@pytest_asyncio.fixture(autouse=True)
async def _reset_db():
    """Recreate the full schema for each test (clean isolation)."""
    shutil.rmtree(_STORAGE_DIR, ignore_errors=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    # Drop any cached detection stack so the next request rebuilds against the
    # freshly seeded catalog (isolation between tests).
    app.state.detection_service = None
    yield
    shutil.rmtree(_STORAGE_DIR, ignore_errors=True)


@pytest_asyncio.fixture
async def db() -> AsyncSession:
    """Direct async session for service-level tests."""
    async with async_session_factory() as session:
        yield session


@pytest_asyncio.fixture
async def client() -> AsyncClient:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
