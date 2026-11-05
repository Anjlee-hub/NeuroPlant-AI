
"""Aggregate router for all v1 domain routers.

Each milestone registers its domain router here (auth → M1, scans → M2,
treatment/soil/calendar → M3, voice/assistant/dataset → M4, …).
"""

from fastapi import APIRouter

from app.api.v1.endpoints import (
    analytics,
    assistant,
    auth,
    calendar,
    catalog,
    community,
    consultations,
    experts,
    favorites,
    market,
    marketplace,
    messaging,
    notifications,
    recommendations,
    recovery,
    reviews,
    scans,
    schemes,
    soil,
    users,
    weather,
    yield_estimation,
)

api_router = APIRouter()

# M1 — identity & profiles.
api_router.include_router(auth.router)
api_router.include_router(users.router)

# M2 — AI disease detection.
api_router.include_router(scans.router)
api_router.include_router(catalog.router)

# M3 — treatment, soil intelligence, recovery and calendar.
api_router.include_router(recommendations.router)
api_router.include_router(soil.router)
api_router.include_router(recovery.router)
api_router.include_router(calendar.router)
api_router.include_router(assistant.router)

# M4 — marketplace and communication.
api_router.include_router(marketplace.router)
api_router.include_router(messaging.router)
api_router.include_router(favorites.router)
api_router.include_router(reviews.router)

# M5 — weather, notifications, yield and market intelligence.
api_router.include_router(weather.router)
api_router.include_router(notifications.router)
api_router.include_router(yield_estimation.router)
api_router.include_router(market.router)
api_router.include_router(schemes.router)
api_router.include_router(analytics.router)

# M6 — farmer community and expert connections.
api_router.include_router(community.router)
api_router.include_router(experts.router)
api_router.include_router(consultations.router)
