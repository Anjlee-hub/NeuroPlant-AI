"""Disease detection inference service.

The service composes the serving stack — catalog → classifier → registry — and
exposes :meth:`DetectionService.predict` as the single seam the API layer talks
to. It decorates raw classifier output with everything a scan row needs:

- model provenance (provider, model name/version, dataset version)
- measured inference time (ms)
- ranked candidates

Classification itself is CPU-bound and blocking, so the async
:meth:`predict_async` wrapper offloads it to a worker thread to keep the event
loop responsive (used by the scan endpoint).
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field

from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool

from app.ai.classifiers import build_disease_classifier
from app.ai.datasets import DiseaseCatalog, load_catalog
from app.ai.registry import registry
from app.ai.types import DiseaseClassifier, ImageData, PredictedDisease
from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True)
class ScanResult:
    """The enriched output of one disease detection run, ready for a scan row."""

    disease_id: int | None
    disease_name: str
    crop_id: int | None
    confidence: float
    provider: str
    model_name: str
    model_version: str
    inference_time_ms: float
    dataset_version: str
    severity: str | None = None
    stage: str | None = None
    symptoms: list[str] = field(default_factory=list)
    rankings: list[PredictedDisease] = field(default_factory=list)


class DetectionService:
    """Facade over the registered disease classifier + label catalog."""

    def __init__(
        self,
        classifier: DiseaseClassifier,
        catalog: DiseaseCatalog,
    ) -> None:
        self.classifier = classifier
        self.catalog = catalog

    @classmethod
    async def build(cls, db: AsyncSession) -> DetectionService:
        """Load the label catalog and compose+register the serving classifier.

        Model artifacts load lazily on first predict; without one the build
        registers the rule baseline so detection works offline/untrained. The
        registry entry is (re)registered on each build — idempotent replace —
        so the last built stack always wins without a restart.
        """
        catalog = await load_catalog(db)
        classifier = build_disease_classifier(catalog)
        registry.register(classifier.capability, classifier)
        info = classifier.model_info
        logger.info(
            "detection_stack_ready",
            provider=info.provider,
            model=info.name,
            version=info.version,
            dataset_version=catalog.version,
        )
        return cls(classifier, catalog)

    def predict(self, image: ImageData) -> ScanResult:
        """Run one detection and return enriched, measured results."""
        start = time.perf_counter()
        prediction = self.classifier.predict(image)
        elapsed_ms = (time.perf_counter() - start) * 1000.0
        model = prediction.model or self.classifier.model_info
        top = prediction.top
        result = ScanResult(
            disease_id=top.disease_id,
            disease_name=top.disease_name,
            crop_id=top.crop_id,
            confidence=top.confidence,
            severity=top.severity,
            stage=top.stage,
            symptoms=top.symptoms,
            provider=model.provider,
            model_name=model.name,
            model_version=model.version,
            inference_time_ms=round(elapsed_ms, 1),
            dataset_version=self.catalog.version,
            rankings=list(prediction.rankings),
        )
        logger.info(
            "scan_predicted",
            provider=result.provider,
            disease=result.disease_name,
            confidence=result.confidence,
            latency_ms=result.inference_time_ms,
        )
        return result

    async def predict_async(self, image: ImageData) -> ScanResult:
        """Event-loop-friendly wrapper; run in a thread, await the result."""
        return await run_in_threadpool(self.predict, image)
