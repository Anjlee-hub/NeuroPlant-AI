"""Yield-estimation and farmer-recorded harvest API schemas."""

from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class HarvestRecordIn(BaseModel):
    schedule_id: int = Field(gt=0)
    actual_yield_kg: float = Field(gt=0, description="Farmer-reported harvested mass in kg")
    area_hectares: float = Field(gt=0, description="Area harvested in hectares")
    harvested_on: date


class HarvestRecordOut(HarvestRecordIn):
    model_config = ConfigDict(from_attributes=True)

    id: int


class YieldEstimateIn(BaseModel):
    crop_id: int = Field(gt=0)
    area_hectares: float = Field(gt=0, description="Planted area in hectares")
    planting_date: date


class YieldEstimateOut(BaseModel):
    crop_id: int
    crop_name: str
    estimated_yield_kg: float | None = Field(
        description="Unavailable until this farmer has recorded a comparable harvest"
    )
    expected_harvest_date: date | None
    historical_harvest_count: int
    reliability: Literal["unavailable", "low", "moderate"]
    methodology: str
    relevant_factors: list[str]
    assumptions: list[str]
    missing_inputs: list[str]
    is_actual_harvest: Literal[False] = False
