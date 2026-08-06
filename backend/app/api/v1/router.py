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
    recommendations,
    recovery,
    scans,
    soil,
    users,
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

# Routers are added milestone-by-milestone:
# M4: voice, dataset
# ...
