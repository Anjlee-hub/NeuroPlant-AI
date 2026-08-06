"""Soil recommendation schemas (M3, Task 3).

Response DTOs for the soil-intelligence engine. Mirrors the treatment schema
(:mod:`app.schemas.recommendation`) so the client renders the whole soil plan
from one self-contained payload: the nine guidance areas, the computed soil
health (label + score + reason), crop suitability, improvement suggestions, and
the disease/severity/confidence context the advice was adapted for.

The health score is computed server-side from the seeded base rating, adjusted
for the scan's severity and detection confidence. Everything else is seeded
content — the engine never hardcodes advice in controllers.
"""

from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.recommendation import RecommendationDiseaseOut

# Canonical severity labels (matched against scan severity / query params).
SOIL_SEVERITIES = ("low", "moderate", "severe")

# Soil-health rating labels (in ascending order of health).
SOIL_HEALTH_LEVELS = ("poor", "fair", "good", "excellent")


class SoilHealthOut(BaseModel):
    """Computed soil health under current conditions (crop + disease context).

    ``score`` is a 0–5 estimate derived from the crop's base soil rating,
    reduced by disease severity and low detection confidence. ``summary``
    explains what influenced the score so the farmer trusts the rating.
    """

    label: str = Field(description="poor | fair | good | excellent")
    score: float = Field(ge=0.0, le=5.0, description="Estimated soil health score (0–5)")
    summary: str = Field(description="Plain-language reason for the rating")


class SoilRecommendationOut(BaseModel):
    """GET /soil/diseases/{id} (or /scans/{id}/soil-recommendations) — the full soil plan.

    Self-contained: the client needs no other call to render a soil care plan.
    Lists are empty (never null) so the frontend can map over them safely.
    """

    catalog_version: str = Field(description="Soil catalog version (e.g. 'v1')")
    disease: RecommendationDiseaseOut

    # ── Nine guidance areas ─────────────────────────────────────────────
    recommended_soil_type: str | None
    ph_range: str | None
    moisture_level: str | None
    drainage: str | None
    organic_matter: str | None
    npk: str | None
    micronutrients: list[str] = Field(default_factory=list)
    compost: str | None
    mulching: str | None

    # ── Soil-health profile ─────────────────────────────────────────────
    soil_health: SoilHealthOut
    soil_suitability: str | None
    improvement_suggestions: list[str] = Field(default_factory=list)

    # ── Disease-aware context the advice was adapted for ────────────────
    disease_soil_notes: str | None
    severity: str | None = Field(description="low | moderate | severe (echoed from the scan)")
    severity_notes: list[str] = Field(default_factory=list)
    confidence: float | None = Field(description="Detection confidence echoed from the scan")
    confidence_note: str | None = Field(description="Set when confidence is low")


class SoilRecommendationCatalogOut(BaseModel):
    """GET /soil/catalog — metadata for one soil catalog version."""

    version: str
    description: str | None
    is_active: bool
    plan_count: int = Field(description="Soil recommendation plans in this catalog")
    updated_at: datetime
