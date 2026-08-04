"""Aggregate router for all v1 domain routers.

Each milestone registers its domain router here (auth → M1, scans → M2,
treatment/soil/calendar → M3, voice/assistant/dataset → M4, …).
"""

from fastapi import APIRouter

from app.api.v1.endpoints import auth, scans, users

api_router = APIRouter()

# M1 — identity & profiles.
api_router.include_router(auth.router)
api_router.include_router(users.router)

# M2 — AI disease detection.
api_router.include_router(scans.router)

# Routers are added milestone-by-milestone:
# M3: treatment, soil, calendar, crop-doctor, assistant
# M4: voice, assistant, dataset
# ...
