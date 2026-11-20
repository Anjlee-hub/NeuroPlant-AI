"""Farmer-history-based yield estimates and actual harvest records."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_current_user, require_roles
from app.db.session import get_db
from app.models.user import User
from app.schemas.yield_estimation import (
    HarvestRecordIn,
    HarvestRecordOut,
    YieldEstimateIn,
    YieldEstimateOut,
)
from app.services.yield_estimation import (
    YieldCropNotFoundError,
    YieldEstimationService,
    YieldScheduleNotFoundError,
)

router = APIRouter(prefix="/yield", tags=["yield"])

Db = Annotated[AsyncSession, Depends(get_db)]
CurrentFarmer = Annotated[User, Depends(require_roles("farmer"))]
CurrentUser = Annotated[User, Depends(get_current_user)]


@router.post("/estimates", response_model=YieldEstimateOut)
async def estimate_yield(
    payload: YieldEstimateIn,
    user: CurrentFarmer,
    db: Db,
) -> YieldEstimateOut:
    """Estimate using only the farmer's prior actual harvests of the crop."""
    try:
        return await YieldEstimationService(db).estimate(user.id, payload)
    except YieldCropNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/harvests", response_model=HarvestRecordOut, status_code=201)
async def record_harvest(
    payload: HarvestRecordIn,
    user: CurrentFarmer,
    db: Db,
) -> HarvestRecordOut:
    """Record an actual harvest against one of the farmer's own crop schedules."""
    try:
        return await YieldEstimationService(db).record_harvest(user.id, payload)
    except YieldScheduleNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/harvests", response_model=list[HarvestRecordOut])
async def list_harvests(
    user: CurrentUser,
    db: Db,
    crop_id: Annotated[int | None, Query(gt=0)] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
) -> list[HarvestRecordOut]:
    """List only the authenticated user's actual harvest records."""
    return await YieldEstimationService(db).list_harvests(
        user.id,
        crop_id=crop_id,
        limit=limit,
    )
