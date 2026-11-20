"""Farmer-owned agricultural and scheme usage analytics reports."""

import csv
from datetime import date
from io import StringIO
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.analytics import (
    AgriculturalAnalyticsOut,
    SchemeUsageAnalyticsOut,
)
from app.services.analytics import (
    AgriculturalAnalyticsService,
    AnalyticsDateRangeError,
    SchemeUsageAnalyticsService,
)

router = APIRouter(prefix="/analytics", tags=["analytics"])

Db = Annotated[AsyncSession, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]
StartDate = Annotated[date | None, Query(alias="period_start")]
EndDate = Annotated[date | None, Query(alias="period_end")]
CropFilter = Annotated[int | None, Query(gt=0)]


@router.get("/agriculture", response_model=AgriculturalAnalyticsOut)
async def agricultural_analytics(
    user: CurrentUser,
    db: Db,
    period_start: StartDate = None,
    period_end: EndDate = None,
    crop_id: CropFilter = None,
) -> AgriculturalAnalyticsOut:
    try:
        return await AgriculturalAnalyticsService(db).report(
            user.id,
            period_start=period_start,
            period_end=period_end,
            crop_id=crop_id,
        )
    except AnalyticsDateRangeError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


def _csv_cell(value: object) -> object:
    if isinstance(value, str) and value.lstrip(" \t\r\n").startswith(("=", "+", "-", "@")):
        return "'" + value
    return value


@router.get("/agriculture/export.csv")
async def export_agricultural_analytics(
    user: CurrentUser,
    db: Db,
    period_start: StartDate = None,
    period_end: EndDate = None,
    crop_id: CropFilter = None,
) -> Response:
    try:
        report = await AgriculturalAnalyticsService(db).report(
            user.id,
            period_start=period_start,
            period_end=period_end,
            crop_id=crop_id,
        )
    except AnalyticsDateRangeError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    content = StringIO(newline="")
    writer = csv.writer(content)
    writer.writerow(["metric", "category", "value"])
    writer.writerow(["actual_harvests", "", report.actual_harvests])
    writer.writerow(["actual_yield_kg", "", report.actual_yield_kg])
    writer.writerow(["calendar_tasks", "all", report.total_calendar_tasks])
    writer.writerow(["calendar_tasks", "completed", report.completed_calendar_tasks])
    for unavailable in report.unavailable_data:
        writer.writerow(["unavailable_data", _csv_cell(unavailable), ""])
    for disease in report.disease_occurrences:
        writer.writerow(
            [
                "disease_occurrence",
                _csv_cell(f"{disease.disease_name} ({disease.severity or 'unspecified'})"),
                disease.count,
            ]
        )
    for comparison in report.yield_comparisons:
        writer.writerow(
            [
                "yield_comparison_kg_per_hectare",
                _csv_cell(comparison.crop_name),
                comparison.difference_kg_per_hectare,
            ]
        )
    return Response(
        content=content.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="agricultural-analytics.csv"'},
    )


@router.get("/schemes", response_model=SchemeUsageAnalyticsOut)
async def scheme_usage_analytics(
    user: CurrentUser,
    db: Db,
    period_start: StartDate = None,
    period_end: EndDate = None,
    crop_name: Annotated[str | None, Query(min_length=1, max_length=120)] = None,
    state_code: Annotated[str | None, Query(min_length=2, max_length=8)] = None,
) -> SchemeUsageAnalyticsOut:
    try:
        return await SchemeUsageAnalyticsService(db).report(
            user.id,
            period_start=period_start,
            period_end=period_end,
            crop_name=crop_name,
            state_code=state_code,
        )
    except AnalyticsDateRangeError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
