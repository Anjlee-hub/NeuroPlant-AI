"""NeuroPlant AI — FastAPI application entrypoint.

Run (native dev):
    uvicorn app.main:app --reload

Run (containerized):
    uvicorn app.main:app --host 0.0.0.0 --port 8000
"""

from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.health import router as health_router
from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger
from app.services.auth import (
    AuthError,
    InvalidCredentialsError,
    InvalidMfaError,
    MfaNotEnabledError,
    UserExistsError,
    UserNotFoundError,
)
from app.services.otp import OtpError
from app.services.scan_pipeline import ScanPipelineError

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


# ── Domain exception → HTTP mapping ─────────────────────────────────────
# Service-layer errors are mapped here (not in routers) so business logic
# stays HTTP-free. Handlers are registered per class; FastAPI picks the most
# specific match via MRO, so the base ``AuthError`` handler is the fallback.


def _error_handler(status_code: int):
    async def handler(_: Request, exc: Any) -> JSONResponse:
        return JSONResponse(status_code=status_code, content={"error": {"message": str(exc)}})

    return handler


# Auth (409/401/404/400) and OTP (400).
app.add_exception_handler(UserExistsError, _error_handler(409))
app.add_exception_handler(MfaNotEnabledError, _error_handler(409))
app.add_exception_handler(InvalidCredentialsError, _error_handler(401))
app.add_exception_handler(UserNotFoundError, _error_handler(404))
app.add_exception_handler(InvalidMfaError, _error_handler(400))
app.add_exception_handler(OtpError, _error_handler(400))
app.add_exception_handler(AuthError, _error_handler(400))

# Scan pipeline — typed errors carry their own status_code + machine code.


def _pipeline_error_handler(_: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, ScanPipelineError)
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": exc.code, "message": str(exc)}},
    )


app.add_exception_handler(ScanPipelineError, _pipeline_error_handler)
