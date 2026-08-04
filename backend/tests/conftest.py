"""Test fixtures.

Environment must be configured *before* ``app`` is imported, because the
settings object and the async engine are created at import time.
"""

import os

os.environ.setdefault(
    "DATABASE_URL",
    "sqlite+aiosqlite:///./test-neuroplant.db",
)
os.environ.setdefault("ENVIRONMENT", "test")
# Surface OTP codes via the API so the flow is testable without SMS.
os.environ.setdefault("DEBUG", "true")

import pytest_asyncio
from app.db.session import Base, engine
from app.main import app  # noqa: F401  (import populates app + metadata)
from app.models import *  # noqa: F401,F403  (register every model on Base.metadata)
from httpx import ASGITransport, AsyncClient


@pytest_asyncio.fixture(autouse=True)
async def _reset_db():
    """Recreate the full schema for each test (clean isolation)."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield


@pytest_asyncio.fixture
async def client() -> AsyncClient:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
