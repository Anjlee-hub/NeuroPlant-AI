"""Unit tests for the AI module structure (registry, preprocess seam, labels)."""

import pytest
from app.ai import registry
from app.ai.datasets import DATASET_VERSION, build_label_map
from app.ai.preprocess import (
    ImageValidationError,
    get_preprocessor,
    register_preprocessor,
)
from app.ai.registry import CapabilityNotRegisteredError
from app.ai.types import ModelInfo


class _FakeClassifier:
    capability = "disease"
    model_info = ModelInfo(name="fake", capability="disease", provider="baseline", version="0")


def test_registry_register_and_get():
    fake = _FakeClassifier()
    registry.register("disease", fake)
    try:
        assert registry.get("disease") is fake
        assert registry.is_available("disease")
        assert registry.available() == ["disease"]
    finally:
        registry.unregister("disease")


def test_registry_unknown_capability_raises():
    registry.unregister("pest")
    with pytest.raises(CapabilityNotRegisteredError):
        registry.get("pest")


def test_registry_can_be_replaced():
    first = _FakeClassifier()
    second = _FakeClassifier()
    registry.register("disease", first)
    registry.register("disease", second)
    try:
        assert registry.get("disease") is second
    finally:
        registry.unregister("disease")


class _Disease:
    """Duck-typed Disease (id/name) for pure label-map tests."""

    def __init__(self, id: int, name: str) -> None:
        self.id = id
        self.name = name


def test_build_label_map_is_deterministic_and_dedupes():
    diseases = [_Disease(3, "Blight"), _Disease(7, "Rust"), _Disease(1, "Blight")]
    catalog = build_label_map(diseases)  # type: ignore[arg-type]
    assert catalog.version == DATASET_VERSION
    assert catalog.class_count == 2
    assert catalog.label_map == {"Blight": 0, "Rust": 1}
    # Duplicate name: last row's id wins for the reverse lookup.
    assert catalog.disease_ids["Blight"] == 1
    assert catalog.disease_ids["Rust"] == 7


def test_build_label_map_empty():
    catalog = build_label_map([])
    assert catalog.class_count == 0
    assert catalog.label_map == {}


class _FakePreprocessor:
    def validate(self, image):
        return image

    def preprocess(self, image):
        return None

    def augment(self, image):
        return [image]


def test_preprocessor_registry_roundtrip():
    register_preprocessor("default", _FakePreprocessor())
    assert get_preprocessor("default") is not None


def test_preprocessor_registry_unknown_raises():
    with pytest.raises(ImageValidationError):
        get_preprocessor("nope")
