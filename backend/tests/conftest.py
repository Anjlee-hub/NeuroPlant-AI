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

import pytest
from app.main import app
from httpx import ASGITransport, AsyncClient


@pytest.fixture
async def client() -> AsyncClient:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
