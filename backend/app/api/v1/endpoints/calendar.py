"""Smart crop calendar endpoints (M3, Task 5).

The Farmer Calendar is the per-crop planning surface. Catalog reads are public
(any authenticated user can browse growth-stage templates); everything else is
user-scoped: schedules and their tasks are owned rows, so every task operation
resolves through the schedule's owner and answers ``404`` for other users' rows.
The service owns all calendar policy (task generation, disease adaptation,
bucketing); these handlers only map HTTP semantics.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.calendar import (
    CalendarCropOut,
    CalendarTaskOut,
    CalendarTaskUpdate,
    CropCalendarOut,
    CustomTaskIn,
    FarmerCalendarOut,
    ScheduleIn,
)
from app.services.calendar import CalendarService

router = APIRouter(prefix="/calendar", tags=["calendar"])

Db = Annotated[AsyncSession, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]


@router.get("/crops", response_model=list[CalendarCropOut])
async def list_calendar_crops(user: CurrentUser, db: Db) -> list[CalendarCropOut]:
    """Every crop with a growth-stage template (for the crop picker).

    Returns the planting window + per-stage day counts so the UI can render the
    timeline before a schedule exists.
    """
    return await CalendarService(db).crops()


@router.post(
    "/crops/{crop_id}/schedule",
    response_model=CropCalendarOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_schedule(
    crop_id: int, payload: ScheduleIn, user: CurrentUser, db: Db
) -> CropCalendarOut:
    """Start (or refresh) the farmer's schedule for one crop.

    ``planting_date`` defaults to today when inside the crop's sowing window,
    otherwise the start of the next window. Idempotent: an existing schedule is
    returned unchanged unless ``regenerate`` is set.
    """
    return await CalendarService(db).schedule(
        user,
        crop_id,
        payload.planting_date,
        regenerate=payload.regenerate,
    )


@router.get("", response_model=FarmerCalendarOut)
async def get_farmer_calendar(user: CurrentUser, db: Db) -> FarmerCalendarOut:
    """The Farmer Calendar dashboard: every scheduled crop + bucket counts."""
    return await CalendarService(db).dashboard(user)


@router.post(
    "/tasks",
    response_model=CalendarTaskOut,
    status_code=status.HTTP_201_CREATED,
)
async def add_custom_task(payload: CustomTaskIn, user: CurrentUser, db: Db) -> CalendarTaskOut:
    """Add a farmer-typed note / to-do to one of the user's schedules."""
    return await CalendarService(db).add_custom_task(user, payload)


@router.patch("/tasks/{task_id}", response_model=CalendarTaskOut)
async def update_task(
    task_id: int, payload: CalendarTaskUpdate, user: CurrentUser, db: Db
) -> CalendarTaskOut:
    """Complete / snooze / re-title / re-date / note one task (partial)."""
    return await CalendarService(db).update_task(user, task_id, payload)


@router.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(task_id: int, user: CurrentUser, db: Db) -> None:
    """Remove a task from the user's schedule."""
    await CalendarService(db).delete_task(user, task_id)
