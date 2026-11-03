"""Structured farmer-scoped analytics report schemas."""

from datetime import date

from pydantic import BaseModel


class DiseaseOccurrenceOut(BaseModel):
    crop_id: int | None
    disease_name: str
    severity: str | None
    count: int


class CategoryCountOut(BaseModel):
    category: str | None
    count: int


class CropYieldComparisonOut(BaseModel):
    crop_id: int
    crop_name: str
    actual_harvests: int
    actual_yield_kg_per_hectare: float | None
    estimates: int
    estimated_yield_kg_per_hectare: float | None
    difference_kg_per_hectare: float | None


class AgriculturalAnalyticsOut(BaseModel):
    period_start: date
    period_end: date
    crop_id: int | None
    disease_occurrences: list[DiseaseOccurrenceOut]
    treatment_progress: list[CategoryCountOut]
    calendar_activity: list[CategoryCountOut]
    total_calendar_tasks: int
    completed_calendar_tasks: int
    actual_harvests: int
    actual_yield_kg: float
    yield_comparisons: list[CropYieldComparisonOut]
    weather_risk_data_available: bool = False
    unavailable_data: list[str]


class SchemeUsageTrendOut(BaseModel):
    date: date
    count: int


class SchemeUsageAnalyticsOut(BaseModel):
    period_start: date
    period_end: date
    total_schemes_viewed: int
    eligibility_checks: int
    applications: int = 0
    application_tracking_available: bool = False
    usage_by_crop: list[CategoryCountOut]
    usage_by_state: list[CategoryCountOut]
    usage_trend: list[SchemeUsageTrendOut]
