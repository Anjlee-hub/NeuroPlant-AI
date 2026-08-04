"""Preprocessing pipeline interface.

The concrete OpenCV-backed provider is pulled in *lazily* on first
:func:`get_preprocessor("default")` so the base install (which does not ship
cv2) stays importable. Everything else talks only to this Protocol, keeping
image validation, normalization and augmentation strategy swappable behind one
seam. Inference never augments: :meth:`Preprocessor.prepare` /
:meth:`Preprocessor.preprocess` are deterministic, and ``augment`` exists
purely for training/TTA callers.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Protocol

from app.ai.types import ImageData

if TYPE_CHECKING:
    import numpy as np


class ImageValidationError(ValueError):
    """Raised for unsupported / corrupt / oversized / malicious images."""


@dataclass(frozen=True)
class PreprocessResult:
    """Everything one inference-time preprocess run produced.

    ``tensor`` is the model input. The other arrays plus ``metadata`` are what
    Grad-CAM (Task 5) needs to build a heatmap over the original image.
    """

    tensor: np.ndarray  # float32 (H, W, 3), channel-last, normalized [0, 1]
    image: np.ndarray  # uint8 (target, target, 3) resized+padded model-input image
    resized: np.ndarray  # uint8 aspect-ratio-preserved resize (pre-pad)
    original: np.ndarray  # uint8 decoded RGB original (orientation-corrected)
    metadata: dict[str, Any] = field(default_factory=dict)  # Grad-CAM prep data


class Preprocessor(Protocol):
    """Validate + normalize source images for model input."""

    def validate(self, image: ImageData) -> ImageData:
        """Return the image unchanged or raise ImageValidationError."""
        ...

    def prepare(self, image: ImageData) -> PreprocessResult:
        """Full inference pipeline: validate, decode, strip EXIF, resize, normalize."""
        ...

    def preprocess(self, image: ImageData) -> np.ndarray:
        """Return a model-ready tensor (normalized, channel-last)."""
        ...

    def augment(self, image: ImageData) -> list[ImageData]:
        """Return a small set of augmented variants (training / TTA only)."""
        ...

    def sanitize(self, image: ImageData) -> ImageData:
        """Return EXIF-stripped, re-encoded bytes safe for storage."""
        ...

    def encode_jpeg(self, rgb: np.ndarray) -> ImageData:
        """Re-encode an RGB uint8 array as a clean JPEG (storable, EXIF-free).

        Used by the scan pipeline to persist the padded model-input image for
        explainability (Task 5 Grad-CAM overlay target).
        """
        ...


_PREPROCESSORS: dict[str, Preprocessor] = {}


def register_preprocessor(name: str, preprocessor: Preprocessor) -> None:
    _PREPROCESSORS[name] = preprocessor


def get_preprocessor(name: str = "default") -> Preprocessor:
    if name == "default" and name not in _PREPROCESSORS:
        # cv2 is an M2+ dependency; the provider registers itself on demand so
        # an artifact-free, cv2-free checkout never fails at import time. If
        # cv2 is absent the provider raises ImageValidationError with a clear
        # message rather than a bare ImportError.
        from app.ai.opencv_preprocess import register_default_preprocessor

        register_default_preprocessor()
    try:
        return _PREPROCESSORS[name]
    except KeyError:
        raise ImageValidationError(f"no preprocessor registered under: {name}") from None
