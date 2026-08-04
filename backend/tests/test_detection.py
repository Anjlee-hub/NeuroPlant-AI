"""Unit tests for the M2 inference layer (Task 2).

Covers the rule-baseline classifier, the lazy TensorFlow classifier's failure
behavior, the provider factory, and the detection service's enrichment logic
(inference time, confidence, model/dataset provenance, rankings).

DB-dependent integration (catalog load + registry wiring through the API) is
deferred to Task 4's ``POST /scans`` tests.
"""

from pathlib import Path

import pytest
from app.ai.classifiers import (
    BASELINE_CONFIDENCE,
    LocalTensorFlowClassifier,
    RuleBaselineClassifier,
    build_disease_classifier,
)
from app.ai.datasets import DATASET_VERSION, DiseaseCatalog, build_label_map
from app.ai.types import (
    ClassifierPrediction,
    ImageData,
    InferenceError,
    ModelInfo,
    ModelUnavailableError,
    PredictedDisease,
)
from app.services.detection import DetectionService, ScanResult

_IMAGE = ImageData(image_bytes=b"fake-jpeg-bytes", content_type="image/jpeg")


class _Disease:
    """Duck-typed Disease (id/name/crop_id) for pure catalog tests."""

    def __init__(self, id: int, name: str, crop_id: int) -> None:
        self.id = id
        self.name = name
        self.crop_id = crop_id


def _catalog() -> DiseaseCatalog:
    diseases = [
        _Disease(1, "Late Blight", 101),
        _Disease(2, "Powdery Mildew", 101),
        _Disease(3, "Leaf Rust", 102),
    ]
    return build_label_map(diseases)  # type: ignore[arg-type]


# ── RuleBaselineClassifier ──────────────────────────────────────────────


def test_rule_baseline_is_deterministic():
    clf = RuleBaselineClassifier(_catalog())
    first = clf.predict(_IMAGE).top
    second = clf.predict(_IMAGE).top
    assert first.disease_name == second.disease_name
    assert first.confidence == BASELINE_CONFIDENCE
    assert clf.model_info.provider == "baseline"


def test_rule_baseline_maps_to_catalog_rows():
    catalog = _catalog()
    top = RuleBaselineClassifier(catalog).predict(_IMAGE).top
    assert top.disease_name in catalog.label_map
    assert catalog.disease_ids[top.disease_name] == top.disease_id
    assert catalog.disease_crops[top.disease_name] == top.crop_id


def test_rule_baseline_empty_catalog_raises():
    clf = RuleBaselineClassifier(build_label_map([]))
    with pytest.raises(InferenceError, match="empty"):
        clf.predict(_IMAGE)


# ── LocalTensorFlowClassifier (lazy load, graceful failure) ─────────────


def test_local_tf_missing_artifact_is_unavailable():
    clf = LocalTensorFlowClassifier(_catalog(), "models/nope-missing.keras")
    assert not clf.is_available
    with pytest.raises(ModelUnavailableError):
        clf.predict(_IMAGE)


def test_local_tf_missing_dependency_raises_model_unavailable():
    # Path exists but is not a model; without TF installed the import itself
    # fails, and with TF installed load_model fails — both degrade to
    # ModelUnavailableError rather than crashing.
    clf = LocalTensorFlowClassifier(_catalog(), str(Path(__file__)))
    assert clf.is_available
    with pytest.raises(ModelUnavailableError):
        clf.predict(_IMAGE)


def test_local_tf_provider_metadata():
    clf = LocalTensorFlowClassifier(_catalog(), "nope", name="effnet", version="v2")
    assert clf.model_info.provider == "local_tf"
    assert clf.model_info.name == "effnet"
    assert clf.model_info.version == "v2"


# ── build_disease_classifier factory ────────────────────────────────────


class _Settings:
    disease_model_path = "definitely/missing/artifact.keras"
    disease_model_version = "v0"


class _SettingsWithArtifact:
    disease_model_path = str(Path(__file__))
    disease_model_version = "v0"


def test_factory_falls_back_to_baseline(monkeypatch):
    monkeypatch.setattr("app.ai.classifiers.get_settings", lambda: _Settings())
    clf = build_disease_classifier(_catalog())
    assert isinstance(clf, RuleBaselineClassifier)
    assert clf.model_info.provider == "baseline"


def test_factory_prefers_tf_when_artifact_present(monkeypatch):
    monkeypatch.setattr("app.ai.classifiers.get_settings", lambda: _SettingsWithArtifact())
    clf = build_disease_classifier(_catalog())
    assert isinstance(clf, LocalTensorFlowClassifier)
    assert clf.model_info.provider == "local_tf"


# ── DetectionService (enrichment, timing, provenance, rankings) ─────────


class _FakeClassifier:
    capability = "disease"
    model_info = ModelInfo(name="fake-cnn", capability="disease", provider="local_tf", version="9")

    def __init__(
        self,
        top: PredictedDisease,
        rankings: tuple[PredictedDisease, ...] = (),
    ) -> None:
        self._top = top
        self._rankings = rankings

    def predict(self, image: ImageData) -> ClassifierPrediction:
        return ClassifierPrediction(
            top=self._top,
            rankings=self._rankings,
            model=self.model_info,
        )


class _NoModelClassifier(_FakeClassifier):
    def predict(self, image: ImageData) -> ClassifierPrediction:
        return ClassifierPrediction(top=self._top, rankings=self._rankings, model=None)


def _service() -> DetectionService:
    top = PredictedDisease(disease_name="Late Blight", confidence=0.92, disease_id=1, crop_id=101)
    return DetectionService(_FakeClassifier(top), _catalog())


def test_predict_builds_enriched_scan_result():
    result = _service().predict(_IMAGE)
    assert isinstance(result, ScanResult)
    assert result.disease_id == 1
    assert result.disease_name == "Late Blight"
    assert result.crop_id == 101
    assert result.confidence == 0.92
    assert result.provider == "local_tf"
    assert result.model_name == "fake-cnn"
    assert result.model_version == "9"
    assert result.dataset_version == DATASET_VERSION
    assert result.inference_time_ms >= 0.0
    assert result.rankings == []


def test_predict_preserves_rankings():
    top = PredictedDisease(disease_name="Late Blight", confidence=0.92, disease_id=1)
    runner_up = PredictedDisease(disease_name="Powdery Mildew", confidence=0.7, disease_id=2)
    clf = _FakeClassifier(top, rankings=(runner_up,))
    result = DetectionService(clf, _catalog()).predict(_IMAGE)
    assert len(result.rankings) == 1
    assert result.rankings[0].disease_name == "Powdery Mildew"
    assert result.rankings[0].confidence == 0.7


def test_predict_falls_back_to_classifier_model_info():
    top = PredictedDisease(disease_name="Leaf Rust", confidence=0.5, disease_id=3)
    svc = DetectionService(_NoModelClassifier(top), _catalog())
    result = svc.predict(_IMAGE)
    assert result.provider == "local_tf"
    assert result.model_version == "9"


async def test_predict_async_matches_sync():
    svc = _service()
    assert await svc.predict_async(_IMAGE) == svc.predict(_IMAGE)
