"""Transparent yield estimates based only on farmer-recorded harvest history."""

from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.calendar import CropSchedule
from app.models.catalog import Crop
from app.models.harvest import HarvestRecord
from app.models.yield_estimate import YieldEstimateRecord
from app.schemas.yield_estimation import (
    HarvestRecordIn,
    HarvestRecordOut,
    YieldEstimateIn,
    YieldEstimateOut,
)


class YieldCropNotFoundError(Exception):
    """The requested crop does not exist."""


class YieldScheduleNotFoundError(Exception):
    """The crop schedule is missing or belongs to another user."""


class YieldEstimationService:
    """Estimate a farmer's expected harvest from that farmer's actual history.

    This deliberately does not apply generic crop-yield factors: the project
    has no verified yield baseline, soil measurements, or historical weather
    records. The estimate is area multiplied by the mean kg/hectare from the
    current user's recorded harvests of the same crop.
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def record_harvest(self, user_id: int, payload: HarvestRecordIn) -> HarvestRecordOut:
        schedule = await self.db.scalar(
            select(CropSchedule).where(
                CropSchedule.id == payload.schedule_id,
                CropSchedule.user_id == user_id,
            )
        )
        if schedule is None:
            raise YieldScheduleNotFoundError("Crop schedule not found.")

        record = HarvestRecord(
            user_id=user_id,
            schedule_id=schedule.id,
            actual_yield_kg=payload.actual_yield_kg,
            area_hectares=payload.area_hectares,
            harvested_on=payload.harvested_on,
        )
        self.db.add(record)
        await self.db.commit()
        await self.db.refresh(record)
        return HarvestRecordOut.model_validate(record)

    async def list_harvests(
        self, user_id: int, *, crop_id: int | None = None, limit: int = 100
    ) -> list[HarvestRecordOut]:
        statement = (
            select(HarvestRecord)
            .join(CropSchedule, CropSchedule.id == HarvestRecord.schedule_id)
            .where(HarvestRecord.user_id == user_id, CropSchedule.user_id == user_id)
            .order_by(HarvestRecord.harvested_on.desc(), HarvestRecord.id.desc())
            .limit(limit)
        )
        if crop_id is not None:
            statement = statement.where(CropSchedule.crop_id == crop_id)
        records = await self.db.scalars(statement)
        return [HarvestRecordOut.model_validate(row) for row in records]

    async def estimate(self, user_id: int, payload: YieldEstimateIn) -> YieldEstimateOut:
        crop = await self.db.get(Crop, payload.crop_id)
        if crop is None:
            raise YieldCropNotFoundError("Crop not found.")

        result = await self.db.execute(
            select(
                func.avg(HarvestRecord.actual_yield_kg / HarvestRecord.area_hectares),
                func.count(HarvestRecord.id),
            )
            .join(CropSchedule, CropSchedule.id == HarvestRecord.schedule_id)
            .where(
                HarvestRecord.user_id == user_id,
                CropSchedule.user_id == user_id,
                CropSchedule.crop_id == crop.id,
            )
        )
        avg_yield_per_hectare, sample_count = result.one()

        sample_count = int(sample_count or 0)
        estimate = (
            round(float(avg_yield_per_hectare) * payload.area_hectares, 2)
            if avg_yield_per_hectare is not None
            else None
        )
        reliability = "moderate" if sample_count >= 3 else "low" if sample_count else "unavailable"
        expected_harvest_date = (
            payload.planting_date + timedelta(days=crop.growth_days)
            if crop.growth_days is not None
            else None
        )
        missing_inputs = [
            "Historical weather observations for this field",
            "Measured soil test results",
            "A validated crop- and region-specific yield baseline",
        ]
        if sample_count == 0:
            missing_inputs.insert(0, "A farmer-recorded actual harvest for this crop")

        schedule_id = await self.db.scalar(
            select(CropSchedule.id).where(
                CropSchedule.user_id == user_id,
                CropSchedule.crop_id == crop.id,
            )
        )
        self.db.add(
            YieldEstimateRecord(
                user_id=user_id,
                crop_id=crop.id,
                schedule_id=schedule_id,
                planting_date=payload.planting_date,
                area_hectares=payload.area_hectares,
                estimated_yield_kg=estimate,
                historical_harvest_count=sample_count,
                reliability=reliability,
                created_at=datetime.now(UTC),
            )
        )
        await self.db.commit()

        return YieldEstimateOut(
            crop_id=crop.id,
            crop_name=crop.common_name or crop.name,
            estimated_yield_kg=estimate,
            expected_harvest_date=expected_harvest_date,
            historical_harvest_count=sample_count,
            reliability=reliability,
            methodology=(
                "For this farmer, multiply planted area by the mean kg/hectare "
                "from their recorded harvests of this crop. No generic yield "
                "figures or unmeasured weather, soil, or disease adjustments are used."
            ),
            relevant_factors=[
                f"Planting date: {payload.planting_date.isoformat()}",
                (
                    f"Catalog growth duration: {crop.growth_days} days"
                    if crop.growth_days is not None
                    else "Catalog growth duration is unavailable"
                ),
                f"Comparable farmer-recorded harvests: {sample_count}",
            ],
            assumptions=[
                "Past recorded harvests are representative of the current crop and field.",
                "The farmer-reported area and harvested mass are accurate.",
            ],
            missing_inputs=missing_inputs,
        )
