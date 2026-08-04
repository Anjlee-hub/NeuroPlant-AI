"""Aggregate router for all v1 domain routers.

Each milestone registers its domain router here (auth → M1, scans → M2,
treatment/soil/calendar → M3, voice/assistant/dataset → M4, …).
"""

from fastapi import APIRouter

api_router = APIRouter()

# Routers are added milestone-by-milestone:
# M1: from app.api.v1.endpoints import auth, users
# M2: from app.api.v1.endpoints import scans
# ...
