"""NeuroPlant AI — FastAPI application entrypoint.

Run (native dev):
    uvicorn app.main:app --reload

Run (containerized):
    uvicorn app.main:app --host 0.0.0.0 --port 8000
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.health import router as health_router
from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger

settings = get_settings()
logger = get_logger("app.main")


@asynccontextmanager
async def lifespan(_: FastAPI):
    configure_logging()
    logger.info("starting", environment=settings.environment)
    yield
    logger.info("shutting down")


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="AI-powered Agriculture Platform — REST API.",
    lifespan=lifespan,
    openapi_url=f"{settings.api_prefix}/openapi.json",
)

# CORS — tighten to the configured origin allow-list (env-managed).
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ops probes are unversioned.
app.include_router(health_router)

# Versioned domain routers.
app.include_router(api_router, prefix=settings.api_prefix)


@app.get("/", include_in_schema=False)
async def root() -> dict[str, str]:
    return {
        "service": settings.app_name,
        "docs": "/docs",
        "health": "/health",
    }
