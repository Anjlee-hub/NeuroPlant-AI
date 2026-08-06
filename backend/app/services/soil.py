"""Soil recommendation service (M3, Task 3).

Read-only access to the active ``SoilRecommendationCatalog``, mirroring
:mod:`app.services.recommendations`. The engine is fully data-driven: every
guidance area and severity note comes from the seeded ``SoilRecommendation``
rows (curated in ``app.db.soil_seed_data``) — controllers never hardcode advice.

``SoilContext`` is the explicit, future-ready seam: today it carries the signals
the scan already knows (crop, disease, severity, confidence). Weather,
location, and real soil-test data will be added as context fields later and
flow through the same :meth:`SoilRecommendationService.health` pipeline without
changing the API — the schema is extended, not redesigned.

The computed soil health is a 0–5 estimate built from the crop's seeded base
rating, then adjusted for disease severity and low detection confidence. The
rating policy (penalties + label thresholds) lives here as documented constants;
the *content* (which severity moves the score how much, what to suggest) lives
in the seed catalog.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.logging import get_logger
from app.models.catalog import Disease
from app.models.scan import Scan
from app.models.soil import SoilRecommendation, SoilRecommendationCatalog
from app.schemas.recommendation import RecommendationDiseaseOut
from app.schemas.soil import SoilHealthOut, SoilRecommendationCatalogOut, SoilRecommendationOut

logger = get_logger(__name__)

# ── Soil-health rating policy ─────────────────────────────────────────────
# These are documented *policy* constants (not content): the base score per
# seeded rating, the severity penalty, and the low-confidence penalty.

BASE_HEALTH_SCORE: dict[str, float] = {"excellent": 5.0, "good": 4.0, "fair": 3.0, "poor": 2.0}

SEVERITY_PENALTY: dict[str, float] = {"severe": 1.0, "moderate": 0.5, "low": 0.0}

CONFIDENCE_LOW_THRESHOLD: float = 0.55
CONFIDENCE_PENALTY: float = 0.5

LOW_CONFIDENCE_NOTE = (
    "Detection confidence is low — re-scan or confirm the diagnosis before acting "
    "on this soil advice."
)

# Label thresholds on the 0–5 score (inclusive lower bounds).
_LABEL_THRESHOLDS: tuple[tuple[str, float], ...] = (
    ("excellent", 4.25),
    ("good", 3.25),
    ("fair", 2.25),
)


class SoilNotFoundError(Exception):
    """No soil plan exists for the requested disease in the active catalog."""


class SoilCatalogUnavailableError(Exception):
    """The soil catalog has not been seeded yet."""


@dataclass(frozen=True)
class SoilContext:
    """Signals that shape soil advice today — the future-ready extension seam.

    New signals (weather, location, soil-test results) become new optional
    fields here and feed :meth:`SoilRecommendationService.health`; the rest of
    the service and every endpoint stay unchanged.
    """

    disease_id: int | None
    disease_name: str | None
    severity: str | None = None
    confidence: float | None = None


class SoilRecommendationService:
    """Resolve soil plans from the active catalog and compute soil health."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def _active_catalog(self) -> SoilRecommendationCatalog:
        """The one active soil catalog (503 when the seeder never ran)."""
        catalog = await self.db.scalar(
            select(SoilRecommendationCatalog).where(SoilRecommendationCatalog.is_active.is_(True))
        )
        if catalog is None:
            raise SoilCatalogUnavailableError(
                "The soil catalog has not been seeded yet; run `python -m app.db.seed`."
            )
        return catalog

    async def catalog(self) -> SoilRecommendationCatalogOut:
        """Metadata for the active soil catalog version, incl. plan count."""
        catalog = await self._active_catalog()
        count = (
            await self.db.scalar(
                select(func.count())
                .select_from(SoilRecommendation)
                .where(SoilRecommendation.catalog_id == catalog.id)
            )
            or 0
        )
        return SoilRecommendationCatalogOut(
            version=catalog.version,
            description=catalog.description,
            is_active=catalog.is_active,
            plan_count=int(count),
            updated_at=catalog.updated_at,
        )

    async def for_disease(
        self,
        disease_id: int,
        *,
        severity: str | None = None,
        confidence: float | None = None,
    ) -> SoilRecommendationOut:
        """Full soil plan for one catalog disease, adapted to severity/confidence."""
        catalog = await self._active_catalog()
        row = await self._load(catalog.id, disease_id)
        if row is None:
            raise SoilNotFoundError(
                f"No soil plan found for disease {disease_id} in catalog {catalog.version}"
            )
        return self._to_out(catalog, row, severity=severity, confidence=confidence)

    async def for_scan(self, scan: Scan) -> SoilRecommendationOut:
        """Soil plan for the disease a scan predicted, adapted to the scan's
        severity + confidence (by id, then by name)."""
        catalog = await self._active_catalog()
        row: SoilRecommendation | None = None
        if scan.disease_id is not None:
            row = await self._load(catalog.id, scan.disease_id)
        if row is None and scan.disease_name:
            row = await self._load_by_name(catalog.id, scan.disease_name)
        if row is None:
            raise SoilNotFoundError(
                f"No soil plan found for scan {scan.id} ({scan.disease_name or 'unknown'}) "
                f"in catalog {catalog.version}"
            )
        return self._to_out(
            catalog, row, severity=scan.severity, confidence=scan.confidence
        )

    # ── Internals ──────────────────────────────────────────────────────

    async def _load(self, catalog_id: int, disease_id: int) -> SoilRecommendation | None:
        """A soil-plan row with its disease (and crop) eagerly loaded."""
        return await self.db.scalar(
            select(SoilRecommendation)
            .options(selectinload(SoilRecommendation.disease).selectinload(Disease.crop))
            .where(
                SoilRecommendation.catalog_id == catalog_id,
                SoilRecommendation.disease_id == disease_id,
            )
        )

    async def _load_by_name(
        self, catalog_id: int, disease_name: str
    ) -> SoilRecommendation | None:
        """A soil-plan row whose catalog disease name matches ``disease_name``."""
        return await self.db.scalar(
            select(SoilRecommendation)
            .options(selectinload(SoilRecommendation.disease).selectinload(Disease.crop))
            .join(Disease, Disease.id == SoilRecommendation.disease_id)
            .where(
                SoilRecommendation.catalog_id == catalog_id,
                Disease.name == disease_name,
            )
        )

    def _to_out(
        self,
        catalog: SoilRecommendationCatalog,
        row: SoilRecommendation,
        *,
        severity: str | None,
        confidence: float | None,
    ) -> SoilRecommendationOut:
        """ORM plan row + request context -> self-contained response DTO."""
        disease = row.disease
        crop_name = disease.crop.common_name if disease.crop is not None else None

        raw_severity_notes = (row.severity_notes or {}).get(severity)
        if raw_severity_notes is None:
            severity_notes: list[str] = []
        elif isinstance(raw_severity_notes, str):  # tolerate a single-string seed
            severity_notes = [raw_severity_notes]
        else:
            severity_notes = list(raw_severity_notes)

        improvement = list(row.improvement_suggestions or [])
        improvement += list((row.severity_suggestions or {}).get(severity, []))

        return SoilRecommendationOut(
            catalog_version=catalog.version,
            disease=RecommendationDiseaseOut(
                id=disease.id,
                name=disease.name,
                crop_id=disease.crop_id,
                crop_name=crop_name,
            ),
            recommended_soil_type=row.recommended_soil_type,
            ph_range=row.ph_range,
            moisture_level=row.moisture_level,
            drainage=row.drainage,
            organic_matter=row.organic_matter,
            npk=row.npk,
            micronutrients=list(row.micronutrients or []),
            compost=row.compost,
            mulching=row.mulching,
            soil_health=self.health(row, severity=severity, confidence=confidence),
            soil_suitability=row.soil_suitability,
            improvement_suggestions=improvement,
            disease_soil_notes=row.disease_soil_notes,
            severity=severity,
            severity_notes=severity_notes,
            confidence=confidence,
            confidence_note=(
                LOW_CONFIDENCE_NOTE
                if confidence is not None and confidence < CONFIDENCE_LOW_THRESHOLD
                else None
            ),
        )

    # ── Soil health scoring ────────────────────────────────────────────

    @staticmethod
    def health(
        row: SoilRecommendation,
        *,
        severity: str | None,
        confidence: float | None,
    ) -> SoilHealthOut:
        """Compute the 0–5 soil-health estimate and a plain-language reason.

        ``base_soil_health`` (seeded per crop) sets the starting score; disease
        severity and low detection confidence reduce it. When real soil-test
        data arrives it becomes another input here — this is the single
        extension point for future context.
        """
        base = BASE_HEALTH_SCORE.get(row.base_soil_health or "fair", 3.0)

        reasons: list[str] = []
        severity_penalty = SEVERITY_PENALTY.get(severity or "", 0.0)
        if severity_penalty > 0:
            reasons.append(f"{severity} disease severity")

        low_confidence = (
            confidence is not None and confidence < CONFIDENCE_LOW_THRESHOLD
        )
        if low_confidence:
            reasons.append("low detection confidence")

        penalty = severity_penalty + (CONFIDENCE_PENALTY if low_confidence else 0.0)
        score = round(max(1.0, min(5.0, base - penalty)), 2)
        label = "poor"
        for candidate, threshold in _LABEL_THRESHOLDS:
            if score >= threshold:
                label = candidate
                break

        summary = (
            f"Adjusted for {', '.join(reasons)}."
            if reasons
            else "Based on the crop's usual soil preferences."
        )
        return SoilHealthOut(label=label, score=score, summary=summary)
