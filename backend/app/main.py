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
from fastapi.staticfiles import StaticFiles

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
from app.services.calendar import (
    CalendarPlanNotFoundError,
    CalendarScheduleNotFoundError,
    CalendarTaskNotFoundError,
)
from app.services.favorites import FavoriteNotFoundError, FavoriteValidationError
from app.services.marketplace import (
    CropListingNotFoundError,
    ListingImageUploadError,
    ProductNotFoundError,
    SellerShopNotFoundError,
)
from app.services.messaging import (
    ConversationClosedError,
    ConversationNotFoundError,
    ConversationValidationError,
)
from app.services.notifications import (
    NotificationNotFoundError,
    NotificationValidationError,
)
from app.services.otp import OtpError
from app.services.recommendations import (
    CatalogUnavailableError,
    RecommendationNotFoundError,
)
from app.services.recovery import RecoveryLogNotFoundError
from app.services.reviews import (
    ReviewDuplicateError,
    ReviewNotFoundError,
    ReviewValidationError,
)
from app.services.scan_pipeline import ScanPipelineError
from app.services.scans import ScanNotFoundError
from app.services.soil import SoilCatalogUnavailableError, SoilNotFoundError
from app.services.storage import local_storage_root
from app.services.weather import InvalidLocationError, WeatherProviderError
from app.services.weather_risk import CropNotFoundError

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
    allow_origins=settings.cors_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ops probes are unversioned.
app.include_router(health_router)

# Versioned domain routers.
app.include_router(api_router, prefix=settings.api_prefix)

# ── Media serving (local dev images + heatmaps) ─────────────────────────
if settings.storage_provider == "local":
    app.mount(
        "/media",
        StaticFiles(directory=local_storage_root(), check_dir=False),
        name="media",
    )


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

# Scans — 404 for missing / other-owned / soft-deleted rows (enumeration guard).
app.add_exception_handler(ScanNotFoundError, _error_handler(404))

# Recommendations (M3) — 404 when a disease has no plan in the active catalog;
# 503 when the catalog itself was never seeded (run `python -m app.db.seed`).
app.add_exception_handler(RecommendationNotFoundError, _error_handler(404))
app.add_exception_handler(CatalogUnavailableError, _error_handler(503))

# Soil (M3 T3) — same semantics for the soil-intelligence catalog.
app.add_exception_handler(SoilNotFoundError, _error_handler(404))
app.add_exception_handler(SoilCatalogUnavailableError, _error_handler(503))

# Recovery (M3 T4) — 404 for a log that isn't on the requested scan.
app.add_exception_handler(RecoveryLogNotFoundError, _error_handler(404))

# Calendar (M3 T5) — 404 for a crop without a plan, another user's schedule,
# or another user's task (same enumeration guard as scans/recovery).
app.add_exception_handler(CalendarPlanNotFoundError, _error_handler(404))
app.add_exception_handler(CalendarScheduleNotFoundError, _error_handler(404))
app.add_exception_handler(CalendarTaskNotFoundError, _error_handler(404))

# Marketplace (M4 T1) — 404 for a listing/product that isn't yours or doesn't
# exist, and a seller role with no registered shop (same guard as scans).
app.add_exception_handler(CropListingNotFoundError, _error_handler(404))
app.add_exception_handler(ProductNotFoundError, _error_handler(404))
app.add_exception_handler(SellerShopNotFoundError, _error_handler(404))
# Marketplace (M4 T2) — 422 when a listing photo fails validation.
app.add_exception_handler(ListingImageUploadError, _error_handler(422))

# Messaging (M4 T5) — 404 when a thread isn't the caller's (enumeration guard),
# 409 when a closed thread is messaged, 400 for bad create context (self-contact,
# wrong/missing listing/product/seller).
app.add_exception_handler(ConversationNotFoundError, _error_handler(404))
app.add_exception_handler(ConversationClosedError, _error_handler(409))
app.add_exception_handler(ConversationValidationError, _error_handler(400))

# Favourites (M4 T6) — 404 when a saved row isn't the caller's (enumeration
# guard), 400 for a bad/unknown favourite target.
app.add_exception_handler(FavoriteNotFoundError, _error_handler(404))
app.add_exception_handler(FavoriteValidationError, _error_handler(400))

# Reviews (M4 T6) — 404 when a review isn't the caller's, 409 on a duplicate
# review of the same item, 400 on a bad target / self-review / blank scope.
app.add_exception_handler(ReviewNotFoundError, _error_handler(404))
app.add_exception_handler(ReviewDuplicateError, _error_handler(409))
app.add_exception_handler(ReviewValidationError, _error_handler(400))

# Weather (M5 T1) — 400 for out-of-range coordinates, 404 for an unsupported
# crop, 502 for an upstream weather failure (timeout / HTTP / malformed /
# missing data) when no fallback source is configured. Subclasses of
# WeatherProviderError all resolve here via MRO; the message is generic so
# provider internals never leak.
app.add_exception_handler(InvalidLocationError, _error_handler(400))
app.add_exception_handler(CropNotFoundError, _error_handler(404))
app.add_exception_handler(WeatherProviderError, _error_handler(502))

# Notifications (M5 T2) — 404 for missing/foreign notification (enumeration
# guard), 400 for validation errors (bad type, empty title/message).
app.add_exception_handler(NotificationNotFoundError, _error_handler(404))
app.add_exception_handler(NotificationValidationError, _error_handler(400))

# Scan pipeline — typed errors carry their own status_code + machine code.


def _pipeline_error_handler(_: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, ScanPipelineError)
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": exc.code, "message": str(exc)}},
    )


app.add_exception_handler(ScanPipelineError, _pipeline_error_handler)
