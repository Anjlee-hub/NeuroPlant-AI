"""Database-aggregated analytics scoped to the authenticated farmer."""

from __future__ import annotations

from datetime import UTC, date, datetime, time, timedelta

from sqlalchemy import and_, case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.calendar import CalendarTask, CropSchedule
from app.models.catalog import Crop
from app.models.harvest import HarvestRecord
from app.models.recovery import RecoveryLog
from app.models.scan import Scan
from app.models.scheme import SchemeUsageEvent
from app.models.yield_estimate import YieldEstimateRecord
from app.schemas.analytics import (
    AgriculturalAnalyticsOut,
    CategoryCountOut,
    CropYieldComparisonOut,
    DiseaseOccurrenceOut,
    SchemeUsageAnalyticsOut,
    SchemeUsageTrendOut,
)


class AnalyticsDateRangeError(Exception):
    """The requested date range is invalid."""


def _period(start: date | None, end: date | None) -> tuple[date, date]:
    today = datetime.now(UTC).date()
    period_end = end or today
    period_start = start or period_end - timedelta(days=29)
    if period_start > period_end:
        raise AnalyticsDateRangeError("period_start must not be after period_end.")
    return period_start, period_end


def _bounds(start: date, end: date) -> tuple[datetime, datetime]:
    return (
        datetime.combine(start, time.min, tzinfo=UTC),
        datetime.combine(end + timedelta(days=1), time.min, tzinfo=UTC),
    )


class AgriculturalAnalyticsService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def report(
        self,
        user_id: int,
        *,
        period_start: date | None = None,
        period_end: date | None = None,
        crop_id: int | None = None,
    ) -> AgriculturalAnalyticsOut:
        start, end = _period(period_start, period_end)
        lower, upper = _bounds(start, end)

        scans_query = (
            select(
                Scan.crop_id,
                Scan.disease_name,
                Scan.severity,
                func.count(Scan.id),
            )
            .where(
                Scan.user_id == user_id,
                Scan.deleted_at.is_(None),
                Scan.created_at >= lower,
                Scan.created_at < upper,
            )
            .group_by(Scan.crop_id, Scan.disease_name, Scan.severity)
        )
        recovery_query = (
            select(RecoveryLog.progress, func.count(RecoveryLog.id))
            .join(Scan, Scan.id == RecoveryLog.scan_id)
            .where(
                RecoveryLog.user_id == user_id,
                Scan.user_id == user_id,
                RecoveryLog.applied_at >= lower,
                RecoveryLog.applied_at < upper,
                Scan.deleted_at.is_(None),
            )
            .group_by(RecoveryLog.progress)
        )
        tasks_query = (
            select(
                CalendarTask.kind,
                func.count(CalendarTask.id),
                func.sum(case((CalendarTask.completed_at.is_not(None), 1), else_=0)),
            )
            .join(CropSchedule, CropSchedule.id == CalendarTask.schedule_id)
            .where(
                CropSchedule.user_id == user_id,
                CalendarTask.due_at >= lower,
                CalendarTask.due_at < upper,
            )
            .group_by(CalendarTask.kind)
        )
        if crop_id is not None:
            scans_query = scans_query.where(Scan.crop_id == crop_id)
            tasks_query = tasks_query.where(CropSchedule.crop_id == crop_id)
            recovery_query = recovery_query.where(Scan.crop_id == crop_id)

        scans = await self.db.execute(scans_query)
        recoveries = await self.db.execute(recovery_query)
        tasks = list(await self.db.execute(tasks_query))

        harvest_query = (
            select(
                CropSchedule.id,
                CropSchedule.crop_id,
                func.sum(HarvestRecord.actual_yield_kg),
                func.sum(HarvestRecord.area_hectares),
                func.count(HarvestRecord.id),
            )
            .join(CropSchedule, CropSchedule.id == HarvestRecord.schedule_id)
            .where(
                HarvestRecord.user_id == user_id,
                CropSchedule.user_id == user_id,
                HarvestRecord.harvested_on >= start,
                HarvestRecord.harvested_on <= end,
            )
            .group_by(CropSchedule.id, CropSchedule.crop_id)
        )
        latest_estimate_query = (
            select(
                YieldEstimateRecord.schedule_id,
                func.max(YieldEstimateRecord.created_at).label("latest_at"),
            )
            .where(
                YieldEstimateRecord.user_id == user_id,
                YieldEstimateRecord.schedule_id.is_not(None),
                YieldEstimateRecord.estimated_yield_kg.is_not(None),
                YieldEstimateRecord.created_at < upper,
            )
            .group_by(YieldEstimateRecord.schedule_id)
        )
        if crop_id is not None:
            latest_estimate_query = latest_estimate_query.where(
                YieldEstimateRecord.crop_id == crop_id
            )
        latest_estimate = latest_estimate_query.subquery()
        estimate_query = (
            select(
                YieldEstimateRecord.schedule_id,
                YieldEstimateRecord.crop_id,
                func.avg(
                    YieldEstimateRecord.estimated_yield_kg / YieldEstimateRecord.area_hectares
                ),
                func.count(YieldEstimateRecord.id),
            )
            .join(
                latest_estimate,
                and_(
                    YieldEstimateRecord.schedule_id == latest_estimate.c.schedule_id,
                    YieldEstimateRecord.created_at == latest_estimate.c.latest_at,
                ),
            )
            .where(
                YieldEstimateRecord.user_id == user_id,
                YieldEstimateRecord.schedule_id.is_not(None),
                YieldEstimateRecord.estimated_yield_kg.is_not(None),
            )
            .group_by(YieldEstimateRecord.schedule_id, YieldEstimateRecord.crop_id)
        )
        if crop_id is not None:
            harvest_query = harvest_query.where(CropSchedule.crop_id == crop_id)
            estimate_query = estimate_query.where(YieldEstimateRecord.crop_id == crop_id)

        harvests = list(await self.db.execute(harvest_query))
        estimates = list(await self.db.execute(estimate_query))
        schedule_ids = {row[0] for row in harvests} | {row[0] for row in estimates}
        schedules = {}
        if schedule_ids:
            schedule_rows = await self.db.execute(
                select(
                    CropSchedule.id,
                    CropSchedule.crop_id,
                    Crop.common_name,
                    Crop.name,
                )
                .join(Crop, Crop.id == CropSchedule.crop_id)
                .where(
                    CropSchedule.user_id == user_id,
                    CropSchedule.id.in_(schedule_ids),
                )
            )
            schedules = {
                row.id: (row.crop_id, row.common_name or row.name) for row in schedule_rows
            }

        actual_by_schedule = {
            row[0]: (row[1], float(row[2] or 0), float(row[3] or 0), int(row[4]))
            for row in harvests
        }
        estimate_by_schedule = {row[0]: (row[1], float(row[2]), int(row[3])) for row in estimates}
        comparison_rows: list[CropYieldComparisonOut] = []
        for schedule_id in sorted(schedule_ids):
            crop_id_for_schedule, crop_name = schedules.get(schedule_id, (None, "Unknown crop"))
            if crop_id_for_schedule is None:
                continue
            actual = actual_by_schedule.get(schedule_id)
            estimate = estimate_by_schedule.get(schedule_id)
            actual_per_ha = actual[1] / actual[2] if actual is not None and actual[2] else None
            estimate_per_ha = estimate[1] if estimate is not None else None
            comparison_rows.append(
                CropYieldComparisonOut(
                    crop_id=crop_id_for_schedule,
                    crop_name=crop_name,
                    actual_harvests=actual[3] if actual else 0,
                    actual_yield_kg_per_hectare=(
                        round(actual_per_ha, 2) if actual_per_ha is not None else None
                    ),
                    estimates=estimate[2] if estimate else 0,
                    estimated_yield_kg_per_hectare=(
                        round(estimate_per_ha, 2) if estimate_per_ha is not None else None
                    ),
                    difference_kg_per_hectare=(
                        round(actual_per_ha - estimate_per_ha, 2)
                        if actual_per_ha is not None and estimate_per_ha is not None
                        else None
                    ),
                )
            )

        total_harvests = sum(row[4] for row in harvests)
        total_actual_kg = sum(float(row[2] or 0) for row in harvests)
        total_tasks = sum(int(row[1] or 0) for row in tasks)
        completed_tasks = sum(int(row[2] or 0) for row in tasks)

        return AgriculturalAnalyticsOut(
            period_start=start,
            period_end=end,
            crop_id=crop_id,
            disease_occurrences=[
                DiseaseOccurrenceOut(
                    crop_id=row[0],
                    disease_name=row[1],
                    severity=row[2],
                    count=int(row[3]),
                )
                for row in scans
            ],
            treatment_progress=[
                CategoryCountOut(category=row[0], count=int(row[1])) for row in recoveries
            ],
            calendar_activity=[
                CategoryCountOut(category=row[0], count=int(row[1])) for row in tasks
            ],
            total_calendar_tasks=total_tasks,
            completed_calendar_tasks=completed_tasks,
            actual_harvests=total_harvests,
            actual_yield_kg=round(total_actual_kg, 2),
            yield_comparisons=comparison_rows,
            unavailable_data=[
                "Historical weather-risk assessments are not persisted.",
                "Soil test measurements are not stored in the current data model.",
            ],
        )


class SchemeUsageAnalyticsService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def report(
        self,
        user_id: int,
        *,
        period_start: date | None = None,
        period_end: date | None = None,
        crop_name: str | None = None,
        state_code: str | None = None,
    ) -> SchemeUsageAnalyticsOut:
        start, end = _period(period_start, period_end)
        lower, upper = _bounds(start, end)
        filters = [
            SchemeUsageEvent.user_id == user_id,
            SchemeUsageEvent.created_at >= lower,
            SchemeUsageEvent.created_at < upper,
        ]
        if crop_name:
            filters.append(func.lower(SchemeUsageEvent.crop_name) == crop_name.strip().lower())
        if state_code:
            filters.append(SchemeUsageEvent.state_code == state_code.strip().upper())

        counts = await self.db.execute(
            select(SchemeUsageEvent.action, func.count(SchemeUsageEvent.id))
            .where(*filters)
            .group_by(SchemeUsageEvent.action)
        )
        action_counts = {action: int(count) for action, count in counts}
        crop_counts = await self.db.execute(
            select(SchemeUsageEvent.crop_name, func.count(SchemeUsageEvent.id))
            .where(*filters)
            .group_by(SchemeUsageEvent.crop_name)
            .order_by(SchemeUsageEvent.crop_name)
        )
        state_counts = await self.db.execute(
            select(SchemeUsageEvent.state_code, func.count(SchemeUsageEvent.id))
            .where(*filters)
            .group_by(SchemeUsageEvent.state_code)
            .order_by(SchemeUsageEvent.state_code)
        )
        trends = await self.db.execute(
            select(func.date(SchemeUsageEvent.created_at), func.count(SchemeUsageEvent.id))
            .where(*filters)
            .group_by(func.date(SchemeUsageEvent.created_at))
            .order_by(func.date(SchemeUsageEvent.created_at))
        )
        return SchemeUsageAnalyticsOut(
            period_start=start,
            period_end=end,
            total_schemes_viewed=action_counts.get("view", 0),
            eligibility_checks=action_counts.get("eligibility_check", 0),
            applications=0,
            application_tracking_available=False,
            usage_by_crop=[
                CategoryCountOut(category=row[0], count=int(row[1])) for row in crop_counts
            ],
            usage_by_state=[
                CategoryCountOut(category=row[0], count=int(row[1])) for row in state_counts
            ],
            usage_trend=[
                SchemeUsageTrendOut(date=date.fromisoformat(str(row[0])), count=int(row[1]))
                for row in trends
            ],
        )
