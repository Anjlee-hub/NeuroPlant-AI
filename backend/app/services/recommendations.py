"""Treatment recommendation service (M3, Task 1).

Read-only access to the active ``RecommendationCatalog``. The engine is fully
data-driven: it never hardcodes treatment content — every plan comes from the
seeded ``DiseaseRecommendation`` rows (curated in ``app.db.recommendation_seed_data``).
Requests resolve against the single active catalog version, so activating a new
catalog version is atomic from the API's point of view.

Two lookups are supported:

- ``for_disease`` — the full care plan for a catalog disease
  (``GET /recommendations/diseases/{id}``).
- ``for_scan`` — the plan for the disease a scan predicted (``GET /scans/{id}/recommendations``);
  it resolves by the scan's ``disease_id`` first and falls back to a
  disease-name match so unmapped predictions still get a plan when one exists.
"""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.logging import get_logger
from app.models.catalog import Disease
from app.models.recommendation import DiseaseRecommendation, RecommendationCatalog
from app.models.scan import Scan
from app.schemas.recommendation import (
    ChemicalRecommendationOut,
    DiseaseRecommendationOut,
    HomemadeRemedyOut,
    OrganicRemedyOut,
    RecommendationCatalogOut,
    RecommendationDiseaseOut,
)

logger = get_logger(__name__)


class RecommendationNotFoundError(Exception):
    """No treatment plan exists for the requested disease in the active catalog."""


class CatalogUnavailableError(Exception):
    """The recommendation catalog has not been seeded yet."""


class RecommendationService:
    """Resolve treatment plans from the active catalog."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def _active_catalog(self) -> RecommendationCatalog:
        """The one active catalog version (503 when the seeder never ran)."""
        catalog = await self.db.scalar(
            select(RecommendationCatalog).where(RecommendationCatalog.is_active.is_(True))
        )
        if catalog is None:
            raise CatalogUnavailableError(
                "The treatment catalog has not been seeded yet; run `python -m app.db.seed`."
            )
        return catalog

    async def catalog(self) -> RecommendationCatalogOut:
        """Metadata for the active catalog version, incl. plan count."""
        catalog = await self._active_catalog()
        count = (
            await self.db.scalar(
                select(func.count())
                .select_from(DiseaseRecommendation)
                .where(DiseaseRecommendation.catalog_id == catalog.id)
            )
            or 0
        )
        return RecommendationCatalogOut(
            version=catalog.version,
            description=catalog.description,
            is_active=catalog.is_active,
            disease_count=int(count),
            updated_at=catalog.updated_at,
        )

    async def for_disease(self, disease_id: int) -> DiseaseRecommendationOut:
        """Full care plan for one catalog disease in the active catalog."""
        catalog = await self._active_catalog()
        row = await self._load(catalog.id, disease_id)
        if row is None:
            raise RecommendationNotFoundError(
                f"No treatment plan found for disease {disease_id} in catalog {catalog.version}"
            )
        return self._to_out(catalog, row)

    async def for_scan(self, scan: Scan) -> DiseaseRecommendationOut:
        """Care plan for the disease a scan predicted (by id, then by name)."""
        catalog = await self._active_catalog()
        if scan.disease_id is not None:
            row = await self._load(catalog.id, scan.disease_id)
            if row is not None:
                return self._to_out(catalog, row)
        if scan.disease_name:
            row = await self._load_by_name(catalog.id, scan.disease_name)
            if row is not None:
                return self._to_out(catalog, row)
        raise RecommendationNotFoundError(
            f"No treatment plan found for scan {scan.id} ({scan.disease_name or 'unknown'}) "
            f"in catalog {catalog.version}"
        )

    # ── Internals ──────────────────────────────────────────────────────

    async def _load(self, catalog_id: int, disease_id: int) -> DiseaseRecommendation | None:
        """A plan row with its disease (and crop) eagerly loaded."""
        return await self.db.scalar(
            select(DiseaseRecommendation)
            .options(
                selectinload(DiseaseRecommendation.disease).selectinload(Disease.crop),
            )
            .where(
                DiseaseRecommendation.catalog_id == catalog_id,
                DiseaseRecommendation.disease_id == disease_id,
            )
        )

    async def _load_by_name(
        self, catalog_id: int, disease_name: str
    ) -> DiseaseRecommendation | None:
        """A plan row whose catalog disease name matches ``disease_name``."""
        return await self.db.scalar(
            select(DiseaseRecommendation)
            .options(
                selectinload(DiseaseRecommendation.disease).selectinload(Disease.crop),
            )
            .join(Disease, Disease.id == DiseaseRecommendation.disease_id)
            .where(
                DiseaseRecommendation.catalog_id == catalog_id,
                Disease.name == disease_name,
            )
        )

    @staticmethod
    def _to_out(
        catalog: RecommendationCatalog, row: DiseaseRecommendation
    ) -> DiseaseRecommendationOut:
        """ORM plan row -> self-contained response DTO."""
        disease = row.disease
        crop_name = disease.crop.common_name if disease.crop is not None else None
        return DiseaseRecommendationOut(
            catalog_version=catalog.version,
            disease=RecommendationDiseaseOut(
                id=disease.id,
                name=disease.name,
                crop_id=disease.crop_id,
                crop_name=crop_name,
            ),
            overview=row.overview,
            cause=row.cause,
            symptoms=list(row.symptoms or []),
            severity=row.severity,
            spread_mechanism=row.spread_mechanism,
            homemade_remedies=[HomemadeRemedyOut(**item) for item in (row.homemade_remedies or [])],
            organic_remedies=[OrganicRemedyOut(**item) for item in (row.organic_remedies or [])],
            chemical_recommendations=[
                ChemicalRecommendationOut(**item) for item in (row.chemical_recommendations or [])
            ],
            fertilizer=row.fertilizer,
            watering=row.watering,
            sunlight=row.sunlight,
            temperature=row.temperature,
            humidity=row.humidity,
            prevention_tips=list(row.prevention_tips or []),
            recovery_timeline=row.recovery_timeline,
            isolation=row.isolation,
            monitoring_advice=list(row.monitoring_advice or []),
        )
