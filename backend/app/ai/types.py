"""Core types for the AI serving layer.

Kept dependency-free (no tensorflow / opencv imports) so the module imports
cleanly even before the ML stack is installed; heavy adapters import their
SDKs lazily inside their own modules.
"""

from dataclasses import dataclass, field
from typing import Protocol


class InferenceError(Exception):
    """Base failure for the AI inference pipeline."""


class ModelUnavailableError(InferenceError):
    """A requested classifier or model artifact is not available."""


@dataclass(frozen=True)
class ImageData:
    """A validated source image handed into the classifier pipeline.

    ``source_type`` keeps the detection pipeline blind to origin so drone /
    satellite / IoT imagery is a new ingestion adapter, not a core change
    (see the MediaItem seam in docs/02-sad.md).
    """

    image_bytes: bytes
    content_type: str
    width: int | None = None
    height: int | None = None
    source_type: str = "upload"  # upload | camera | drone | satellite | iot


@dataclass(frozen=True)
class PredictedDisease:
    """One ranked prediction mapped onto the diseases catalog."""

    disease_name: str
    confidence: float
    disease_id: int | None = None
    crop_id: int | None = None
    severity: str | None = None  # low | moderate | severe
    stage: str | None = None
    symptoms: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class ModelInfo:
    """Identity of the model that produced a prediction."""

    name: str
    capability: str  # "disease" for now; pest/soil/yield arrive later
    provider: str  # local_tf | cloud | baseline
    version: str
    status: str = "ready"  # training | staging | production | ready


@dataclass(frozen=True)
class ClassifierPrediction:
    """Top prediction plus the full ranked output."""

    top: PredictedDisease
    rankings: tuple[PredictedDisease, ...] = ()
    model: ModelInfo | None = None


class DiseaseClassifier(Protocol):
    """Predicts disease for a (preprocessed) source image.

    Concrete adapters (local TensorFlow, cloud, rule baseline) implement this.
    """

    capability: str
    model_info: ModelInfo

    def predict(self, image: ImageData) -> ClassifierPrediction: ...
