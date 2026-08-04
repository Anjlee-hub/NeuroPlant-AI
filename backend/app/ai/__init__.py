"""AI serving layer: classifier adapters, preprocessing, model registry.

Serving-side seams only — training pipelines live under ``ai/training/``.
See docs/08-ai-pipeline.md for the training → versioning → serving loop.
"""

from app.ai.preprocess import (
    ImageValidationError,
    get_preprocessor,
    register_preprocessor,
)
from app.ai.registry import CapabilityNotRegisteredError, ModelRegistry, registry
from app.ai.types import (
    ClassifierPrediction,
    DiseaseClassifier,
    ImageData,
    InferenceError,
    ModelInfo,
    ModelUnavailableError,
    PredictedDisease,
)

__all__ = [
    "CapabilityNotRegisteredError",
    "ClassifierPrediction",
    "DiseaseClassifier",
    "ImageData",
    "ImageValidationError",
    "InferenceError",
    "ModelInfo",
    "ModelUnavailableError",
    "ModelRegistry",
    "PredictedDisease",
    "get_preprocessor",
    "register_preprocessor",
    "registry",
]
