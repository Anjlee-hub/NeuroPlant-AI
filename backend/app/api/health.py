"""Liveness + readiness probes.

- ``GET /health`` — process liveness. Always 200 if the process is up.
- ``GET /ready`` — dependency readiness (DB reachable). 200 when ready,
  503 when a dependency is unavailable (used by orchestrators / load balancers).
"""

from fastapi import APIRouter, Response, status

from app.db.session import ping_db

router = APIRouter(tags=["ops"])


@router.get("/health", summary="Liveness probe")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/ready", summary="Readiness probe")
async def ready(response: Response) -> dict[str, str]:
    db_ok = await ping_db()
    if not db_ok:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"status": "unavailable", "database": "down"}
    return {"status": "ready", "database": "up"}
