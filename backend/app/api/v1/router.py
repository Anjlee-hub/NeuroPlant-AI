"""Aggregate router for all v1 domain routers.

Each milestone registers its domain router here (auth → M1, scans → M2,
treatment/soil/calendar → M3, voice/assistant/dataset → M4, …).
"""

from fastapi import APIRouter

from app.api.v1.endpoints import (
    assistant,
    auth,
    calendar,
    catalog,
    favorites,
    marketplace,
    messaging,
    recommendations,
    recovery,
    reviews,
    scans,
    soil,
    users,
    weather,
)

api_router = APIRouter()

# M1 — identity & profiles.
api_router.include_router(auth.router)
api_router.include_router(users.router)

# M2 — AI disease detection.
api_router.include_router(scans.router)
api_router.include_router(catalog.router)  # read-only filter options (Task 7.1)

# M3 — smart treatment recommendation engine (+ soil intelligence + recovery
# + calendar + the rule-based voice AI assistant).
api_router.include_router(recommendations.router)
api_router.include_router(soil.router)
api_router.include_router(recovery.router)
api_router.include_router(calendar.router)
api_router.include_router(assistant.router)

# M4 — farmer marketplace & community (Task 1: marketplace backend foundation).
api_router.include_router(marketplace.router)
# M4 Task 5 — buyer↔seller communication (inquiry/chat system).
api_router.include_router(messaging.router)
# M4 Task 6 — marketplace trust: saved items (favourites) + reviews/ratings.
api_router.include_router(favorites.router)
api_router.include_router(reviews.router)

# M5 — weather intelligence & disease-risk (Task 1: weather + risk foundation).
api_router.include_router(weather.router)

# Routers are added milestone-by-milestone:
# M5: outbreaks, yield, prices, maps, notifications (in progress)
# ...
