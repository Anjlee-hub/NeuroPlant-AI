"""Soil-recommendation endpoints (M3, Task 3).

``GET /soil/catalog`` returns the active soil catalog version's metadata and
``GET /soil/diseases/{id}`` the full, disease-aware soil plan for one disease.
The latter accepts optional ``severity`` / ``confidence`` query parameters so a
farmer (or a future weather/soil-test integration) can preview how the advice
and the computed soil-health score adapt. Content lives entirely in the seeded
catalog — these handlers only read it.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.soil import SoilRecommendationCatalogOut, SoilRecommendationOut
from app.services.soil import SoilRecommendationService

router = APIRouter(prefix="/soil", tags=["soil"])

Db = Annotated[AsyncSession, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]


@router.get("/catalog", response_model=SoilRecommendationCatalogOut)
async def get_soil_catalog(_current_user: CurrentUser, db: Db) -> SoilRecommendationCatalogOut:
    """Metadata for the active soil catalog (version, plan count)."""
    return await SoilRecommendationService(db).catalog()


@router.get("/diseases/{disease_id}", response_model=SoilRecommendationOut)
async def get_disease_soil_recommendation(
    disease_id: int,
    _current_user: CurrentUser,
    db: Db,
    severity: Annotated[
        str | None,
        Query(pattern="^(low|moderate|severe)$", description="How the advice should adapt"),
    ] = None,
    confidence: Annotated[
        float | None, Query(ge=0.0, le=1.0, description="Detection confidence (0–1)")
    ] = None,
) -> SoilRecommendationOut:
    """Complete, self-contained soil plan for one catalog disease.

    ``404`` when the disease has no plan in the active catalog. Optional
    ``severity`` / ``confidence`` adjust the soil-health score and the
    severity-aware notes/suggestions.
    """
    return await SoilRecommendationService(db).for_disease(
        disease_id, severity=severity, confidence=confidence
    )
