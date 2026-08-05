"""Unit tests for :class:`ExplainService` (M2, Task 5.4).

Drives the service directly (no HTTP) against an in-memory :class:`Scan` row:
confidence-band advice, the plain-language explanation text, Grad-CAM
provenance + storage-URL resolution, pipeline-timing passthrough, and
catalog-symptom lookup. Complements the API tests in ``test_explain_api.py``.
"""

import uuid

import pytest
from app.db.seed import seed_catalog
from app.models.scan import Scan
from app.services.explain import ExplainService

_CLIENT_ID = str(uuid.UUID(int=1))

# Full ai_metadata as the pipeline writes it (Task 5.2): top-5 + grad_cam.
_METADATA: dict = {
    "top5": [
        {"disease_name": "Late Blight", "confidence": 0.92, "disease_id": 1, "crop_id": 101},
        {"disease_name": "Early Blight", "confidence": 0.04, "disease_id": 2, "crop_id": 101},
    ],
    "grad_cam": {
        "provider": "baseline",
        "class_name": "Late Blight",
        "time_ms": 18.2,
        "heatmap_path": "1/heatmaps/raw.png",
        "overlay_path": "1/heatmaps/overlay.png",
    },
}


def _scan(**overrides) -> Scan:
    """A Scan row with every field :class:`ExplainService` reads populated."""
    defaults = {
        "id": 7,
        "client_scan_id": _CLIENT_ID,
        "user_id": 1,
        "image_path": "1/scans/leaf.jpg",
        "processed_image_path": "1/processed/leaf.jpg",
        "crop_id": 101,
        "part_type": "leaf",
        "disease_id": 1,
        "disease_name": "Late Blight",
        "confidence": 0.92,
        "severity": "moderate",
        "stage": "early",
        "provider": "baseline",
        "model_name": "rule-baseline",
        "model_version": "baseline-v1",
        "dataset_version": "v1",
        "preprocessing_time_ms": 12.4,
        "inference_time_ms": 8.1,
        "processing_time_ms": 31.9,
        "heatmap_path": "1/heatmaps/overlay.png",
        "ai_metadata": _METADATA,
    }
    defaults.update(overrides)
    return Scan(**defaults)


class _FakeStorage:
    """StorageService stand-in recording the keys passed to ``url()``."""

    def __init__(self) -> None:
        self.calls: list[str] = []

    def save(self, data: bytes, content_type: str, user_id: int, subdir: str = "") -> str:
        raise NotImplementedError  # pragma: no cover - unused by ExplainService

    def read(self, key: str) -> bytes:
        raise NotImplementedError  # pragma: no cover - unused by ExplainService

    def delete(self, key: str) -> None:
        raise NotImplementedError  # pragma: no cover - unused by ExplainService

    def url(self, key: str) -> str:
        self.calls.append(key)
        return f"/media/{key}"


# ── Full payload composition ──────────────────────────────────────────────


async def test_build_composes_full_payload(db):
    payload = await ExplainService(db, _FakeStorage()).build(_scan())

    assert payload.scan_id == 7
    assert payload.disease.name == "Late Blight"
    assert payload.disease.severity == "moderate"
    assert payload.disease.stage == "early"
    assert payload.confidence.top == 0.92
    assert payload.confidence.level == "high"
    assert payload.confidence.advice
    assert [c.disease_name for c in payload.top5] == ["Late Blight", "Early Blight"]
    assert payload.heatmap is not None
    assert payload.heatmap.provider == "baseline"
    assert payload.heatmap.class_name == "Late Blight"
    assert payload.heatmap.time_ms == 18.2
    assert payload.heatmap_url == "/media/1/heatmaps/raw.png"
    assert payload.overlay_url == "/media/1/heatmaps/overlay.png"
    assert payload.timing.preprocessing_time_ms == 12.4
    assert payload.timing.inference_time_ms == 8.1
    assert payload.timing.processing_time_ms == 31.9
    assert payload.timing.heatmap_time_ms == 18.2
    assert payload.model.provider == "baseline"
    assert payload.model.model_version == "baseline-v1"
    assert payload.model.dataset_version == "v1"


async def test_urls_resolve_from_stored_keys(db):
    storage = _FakeStorage()
    await ExplainService(db, storage).build(_scan())
    assert storage.calls == ["1/heatmaps/raw.png", "1/heatmaps/overlay.png"]


async def test_top5_empty_without_metadata(db):
    payload = await ExplainService(db, _FakeStorage()).build(_scan(ai_metadata=None))
    assert payload.top5 == []


# ── Confidence bands + advice ─────────────────────────────────────────────


@pytest.mark.parametrize(
    ("confidence", "level"),
    [(0.9, "high"), (0.7, "medium"), (0.4, "low")],
)
async def test_confidence_level_and_advice(db, confidence, level):
    payload = await ExplainService(db, _FakeStorage()).build(_scan(confidence=confidence))
    assert payload.confidence.top == confidence
    assert payload.confidence.level == level
    assert payload.confidence.advice


# ── Plain-language explanation ────────────────────────────────────────────


async def test_explanation_includes_facts(db):
    payload = await ExplainService(db, _FakeStorage()).build(_scan(confidence=0.92))
    text = payload.explanation
    assert "Late Blight" in text
    assert "92%" in text
    assert "moderate severity" in text
    assert "early" in text
    assert "heatmap overlay" in text


async def test_explanation_omits_heatmap_and_stage_when_absent(db):
    scan = _scan(
        confidence=0.4,
        severity=None,
        stage=None,
        heatmap_path=None,
        ai_metadata={"grad_cam": {"provider": "baseline", "class_name": "Late Blight"}},
    )
    payload = await ExplainService(db, _FakeStorage()).build(scan)
    assert "heatmap overlay" not in payload.explanation
    assert "consistent with" not in payload.explanation


# ── Degradation without a heatmap ────────────────────────────────────────


async def test_degrades_without_heatmap(db):
    scan = _scan(
        confidence=0.6,
        heatmap_path=None,
        ai_metadata={"top5": _METADATA["top5"], "confidence": {"top": 0.6, "level": "medium"}},
    )
    payload = await ExplainService(db, _FakeStorage()).build(scan)
    assert payload.heatmap is None
    assert payload.heatmap_url is None
    assert payload.overlay_url is None
    assert payload.timing.heatmap_time_ms is None
    assert payload.confidence.level == "medium"


async def test_heatmap_timing_none_when_gradcam_missing_time(db):
    scan = _scan(ai_metadata={"grad_cam": {"provider": "baseline", "heatmap_path": "r.png"}})
    payload = await ExplainService(db, _FakeStorage()).build(scan)
    assert payload.timing.heatmap_time_ms is None


# ── Catalog symptom lookup ────────────────────────────────────────────────


async def test_symptoms_lookup_from_catalog(db):
    await seed_catalog(db)
    payload = await ExplainService(db, _FakeStorage()).build(_scan(disease_id=1))
    assert payload.disease.symptoms
    assert "Dark brown concentric-ring spots on older leaves" in payload.disease.symptoms


async def test_symptoms_empty_for_unknown_disease(db):
    payload = await ExplainService(db, _FakeStorage()).build(_scan(disease_id=9999))
    assert payload.disease.symptoms == []
