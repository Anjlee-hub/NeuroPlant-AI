"""Scan explainability payload (M2, Task 5.3).

:class:`ExplainService` turns a persisted :class:`Scan` into the
``GET /scans/{id}/explain`` payload *without* re-running inference: everything
the endpoint needs (Grad-CAM paths, top-5 candidates, confidence metadata, model
provenance) was captured at prediction time (Task 5.2) and stored on the row.
The service only re-reads it, resolves storage URLs, pulls catalog symptoms, and
composes the plain-language explanation + expert advice from the stored facts.

A scan whose heatmap was never produced (explainability unavailable or failed at
upload) still explains the diagnosis — the heatmap fields are simply ``None``.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.catalog import Disease
from app.models.scan import Scan
from app.schemas.scan import (
    ExplainConfidenceOut,
    ExplainDiseaseOut,
    ExplainHeatmapOut,
    ExplainModelOut,
    RankingOut,
    ScanExplainOut,
)
from app.services.detection import confidence_level
from app.services.storage import StorageService

logger = get_logger(__name__)

# Plain-language expert advice per confidence band (Task 5.3). Low-confidence
# scans get an explicit "verify before treating" nudge; medium/high still advise
# a visual cross-check on the plant itself.
_CONFIDENCE_ADVICE: dict[str, str] = {
    "high": (
        "High-confidence result — the pattern is a strong match for this disease. "
        "Treat accordingly, but confirm the symptoms on a couple more leaves first."
    ),
    "medium": (
        "Moderate-confidence result — other diseases can look similar at this stage. "
        "Compare a few more leaves before deciding on treatment."
    ),
    "low": (
        "Low-confidence result — the pattern is ambiguous and may not be this disease. "
        "Retake the photo in even lighting and at close range, or check with a local "
        "agronomist before applying any treatment."
    ),
}


def _explanation(scan: Scan, heatmap_available: bool) -> str:
    """Compose the deterministic plain-language "why" from stored facts."""
    pct = round(scan.confidence * 100)
    focus = (
        " The heatmap overlay marks the image regions the model focused on."
        if heatmap_available
        else ""
    )
    detail = ""
    if scan.severity and scan.stage:
        detail = (
            f" The pattern is consistent with {scan.severity} severity at the {scan.stage} stage."
        )
    return (
        f"This photo was classified as {scan.disease_name} with {pct}% confidence.{focus}{detail}"
    )


class ExplainService:
    """Build the explainability payload for one stored scan."""

    def __init__(self, db: AsyncSession, storage: StorageService) -> None:
        self.db = db
        self.storage = storage

    async def build(self, scan: Scan) -> ScanExplainOut:
        """Assemble the explain payload from stored scan state (no inference)."""
        metadata = scan.ai_metadata or {}
        top5 = metadata.get("top5") or []
        level = confidence_level(scan.confidence)
        grad_cam = metadata.get("grad_cam") or {}

        # The scan's heatmap_path points at the Jet overlay; the raw grayscale
        # map is kept alongside it in ai_metadata (Task 5.2).
        overlay_key = scan.heatmap_path
        raw_key = grad_cam.get("heatmap_path")
        heatmap_available = overlay_key is not None or raw_key is not None

        return ScanExplainOut(
            scan_id=scan.id,
            disease=ExplainDiseaseOut(
                id=scan.disease_id,
                name=scan.disease_name,
                crop_id=scan.crop_id,
                severity=scan.severity,
                stage=scan.stage,
                symptoms=await self._symptoms(scan),
            ),
            confidence=ExplainConfidenceOut(
                top=scan.confidence,
                level=level,
                advice=_CONFIDENCE_ADVICE[level],
            ),
            top5=[
                RankingOut(
                    disease_name=candidate.get("disease_name", ""),
                    confidence=float(candidate.get("confidence", 0.0)),
                    disease_id=candidate.get("disease_id"),
                    crop_id=candidate.get("crop_id"),
                )
                for candidate in top5
            ],
            heatmap=(
                ExplainHeatmapOut(
                    provider=grad_cam.get("provider", "unknown"),
                    class_name=grad_cam.get("class_name", scan.disease_name),
                    time_ms=float(grad_cam.get("time_ms") or 0.0),
                )
                if heatmap_available
                else None
            ),
            heatmap_url=self.storage.url(raw_key) if raw_key else None,
            overlay_url=self.storage.url(overlay_key) if overlay_key else None,
            explanation=_explanation(scan, heatmap_available),
            model=ExplainModelOut(
                provider=scan.provider,
                model_name=scan.model_name,
                model_version=scan.model_version,
                dataset_version=scan.dataset_version,
            ),
        )

    async def _symptoms(self, scan: Scan) -> list[str]:
        """Catalog symptoms for the predicted disease (empty when unknown)."""
        if scan.disease_id is None:
            return []
        disease = await self.db.get(Disease, scan.disease_id)
        if disease is None:
            return []
        return list(disease.symptoms or [])
