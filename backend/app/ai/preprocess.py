"""Preprocessing pipeline interface.

The concrete OpenCV-backed preprocessor (M2) registers itself under "default";
everywhere else talks only to this Protocol, so image validation, normalization
and augmentation strategy stay swappable behind one seam.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

from app.ai.types import ImageData

if TYPE_CHECKING:
    import numpy as np


class ImageValidationError(ValueError):
    """Raised for unsupported / corrupt / oversized images."""


class Preprocessor(Protocol):
    """Validate + normalize source images for model input."""

    def validate(self, image: ImageData) -> ImageData:
        """Return the image unchanged or raise ImageValidationError."""
        ...

    def preprocess(self, image: ImageData) -> np.ndarray:
        """Return a model-ready tensor (normalized, channel-last)."""
        ...

    def augment(self, image: ImageData) -> list[ImageData]:
        """Return a small set of augmented variants (training / TTA)."""
        ...


_PREPROCESSORS: dict[str, Preprocessor] = {}


def register_preprocessor(name: str, preprocessor: Preprocessor) -> None:
    _PREPROCESSORS[name] = preprocessor


def get_preprocessor(name: str = "default") -> Preprocessor:
    try:
        return _PREPROCESSORS[name]
    except KeyError:
        raise ImageValidationError(f"no preprocessor registered under: {name}") from None
