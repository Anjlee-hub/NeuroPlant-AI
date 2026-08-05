"""Treatment-recommendation endpoints (M3, Task 1).

``GET /recommendations/catalog`` returns the active catalog version's metadata
and ``GET /recommendations/diseases/{id}`` the full care plan for one disease.
Both are read-only and resolve against the single active catalog, so the client
never needs to know which version is current. Treatment content lives entirely
in the seeded database — these handlers only read it (no hardcoded advice).
"""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.recommendation import (
    DiseaseRecommendationOut,
    RecommendationCatalogOut,
)
from app.services.recommendations import RecommendationService

router = APIRouter(prefix="/recommendations", tags=["recommendations"])

Db = Annotated[AsyncSession, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]


@router.get("/catalog", response_model=RecommendationCatalogOut)
async def get_catalog(_current_user: CurrentUser, db: Db) -> RecommendationCatalogOut:
    """Metadata for the active treatment catalog (version, plan count)."""
    return await RecommendationService(db).catalog()


@router.get("/diseases/{disease_id}", response_model=DiseaseRecommendationOut)
async def get_disease_recommendation(
    disease_id: int, _current_user: CurrentUser, db: Db
) -> DiseaseRecommendationOut:
    """Complete, self-contained treatment plan for one catalog disease.

    ``404`` when the disease has no plan in the active catalog.
    """
    return await RecommendationService(db).for_disease(disease_id)
