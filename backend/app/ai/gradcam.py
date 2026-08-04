"""Grad-CAM explainability primitives (M2, Task 5).

Produces the spatial heatmap that shows *why* the model looked where it looked,
plus the OpenCV overlay / encoding helpers used to render and persist it. Two
providers implement the same :class:`ExplainabilityProvider` seam:

- :class:`TensorFlowGradCAM` — true gradient-weighted class-activation mapping
  against a Keras CNN (the production path). ``tensorflow`` is imported lazily
  and the provider is only ever built once a model artifact is loaded, so the
  base install and artifact-free checkouts stay importable.
- :class:`RuleBaselineSaliency` — deterministic, artifact-free heatmap used by
  the rule-baseline classifier (and as the no-model fallback). It highlights
  high-contrast / edge-dense regions — where lesion symptoms typically appear —
  using only OpenCV, and is labelled ``provider="baseline"`` so consumers can
  tell it apart from model-backed Grad-CAM.

Every provider returns a normalized float32 heatmap in ``[0, 1]`` sized to the
*original* image, so overlays render at full resolution (high-res export) and
the explain endpoint can blend at any opacity without re-running inference.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Protocol

import numpy as np

from app.ai.preprocess import ImageValidationError, Preprocessor
from app.ai.types import ImageData, InferenceError
from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True)
class HeatmapResult:
    """One generated heatmap plus how long it took to produce."""

    heatmap: np.ndarray  # float32 (H, W) normalized to [0, 1]
    time_ms: float


class ExplainabilityProvider(Protocol):
    """Produces a normalized heatmap for a prediction's target class."""

    capability: str
    provider_name: str

    def heatmap(self, image: ImageData, class_name: str | None = None) -> HeatmapResult:
        """Return a float32 ``(H, W)`` heatmap in ``[0, 1]`` at original size."""
        ...


def _decode_bgr(data: bytes) -> np.ndarray:
    """Decode encoded image bytes to a BGR uint8 array (cv2) or raise."""
    import cv2

    buffer = np.frombuffer(data, dtype=np.uint8)
    bgr = cv2.imdecode(buffer, cv2.IMREAD_COLOR)
    if bgr is None:
        raise ImageValidationError("unable to decode image for heatmap")
    return bgr


class RuleBaselineSaliency:
    """Deterministic saliency heatmap used when no trained CNN is available.

    Highlights high-contrast / edge-dense regions (where lesion symptoms
    typically appear) via a Laplacian edge-energy map smoothed with a large
    Gaussian. Purely OpenCV — no learned weights — so identical inputs always
    produce identical heatmaps (testable, demoable) and it is explicitly
    labelled ``provider="baseline"``.
    """

    capability = "disease"
    provider_name = "baseline"

    def heatmap(self, image: ImageData, class_name: str | None = None) -> HeatmapResult:
        import cv2

        start = time.perf_counter()
        bgr = _decode_bgr(image.image_bytes)
        gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
        # |Laplacian| ≈ local contrast/edge energy; blur aggregates it into a
        # smooth saliency region (large sigma spreads evidence plausibly).
        energy: np.ndarray = np.abs(cv2.Laplacian(gray, cv2.CV_64F)).astype(np.float32)
        energy = cv2.GaussianBlur(energy, (0, 0), sigmaX=16)
        lo, hi = float(energy.min()), float(energy.max())
        heatmap = (energy - lo) / (hi - lo + 1e-9)
        elapsed_ms = (time.perf_counter() - start) * 1000.0
        return HeatmapResult(heatmap=heatmap, time_ms=round(elapsed_ms, 2))


class TensorFlowGradCAM:
    """True gradient-weighted class activation mapping against a Keras CNN.

    ``tensorflow`` is imported lazily on first :meth:`heatmap` so constructing
    this class never forces the ML stack; a missing install surfaces as an
    :class:`InferenceError` rather than an ``ImportError`` crash.
    """

    capability = "disease"
    provider_name = "local_tf"

    def __init__(
        self,
        model: Any,
        preprocessor: Preprocessor,
        label_map: dict[str, int],
        *,
        layer_name: str | None = None,
    ) -> None:
        self._model = model
        self._preprocessor = preprocessor
        self._label_map = label_map
        self._layer_name = layer_name or self._pick_conv_layer(model)

    @staticmethod
    def _pick_conv_layer(model: Any) -> str:
        try:
            import tensorflow as tf
        except ImportError as exc:  # pragma: no cover - exercised in CI envs
            raise InferenceError("tensorflow is not installed; Grad-CAM is unavailable") from exc

        convs = [layer.name for layer in model.layers if isinstance(layer, tf.keras.layers.Conv2D)]
        if not convs:
            raise InferenceError("model has no Conv2D layer to build Grad-CAM from")
        return convs[-1]

    def heatmap(self, image: ImageData, class_name: str | None = None) -> HeatmapResult:
        try:
            import tensorflow as tf
        except ImportError as exc:  # pragma: no cover - exercised in CI envs
            raise InferenceError("tensorflow is not installed; Grad-CAM is unavailable") from exc

        start = time.perf_counter()
        if class_name is None:
            raise InferenceError("class_name is required for Grad-CAM")
        class_index = self._label_map.get(class_name)
        if class_index is None:
            raise InferenceError(f"class {class_name!r} is not in the model label map")

        prepared = self._preprocessor.prepare(image)
        batch = np.expand_dims(prepared.tensor, axis=0)
        conv_layer = self._model.get_layer(self._layer_name)
        grad_model = tf.keras.Model(
            inputs=self._model.inputs,
            outputs=[conv_layer.output, self._model.output],
        )
        with tf.GradientTape() as tape:
            inputs = tf.convert_to_tensor(batch)
            tape.watch(inputs)
            conv_out, logits = grad_model(inputs, training=False)
            loss = logits[0, class_index]
        grads = tape.gradient(loss, conv_out)
        if grads is None:
            raise InferenceError("Grad-CAM gradient is None; cannot build heatmap")

        # GAP the gradients per channel → weights; weighted-sum the feature maps.
        weights = tf.reduce_mean(grads, axis=(1, 2))  # (1, C)
        cam = tf.reduce_sum(weights[:, None, None] * conv_out, axis=-1)[0]
        cam = tf.nn.relu(cam).numpy()
        cam = (cam - cam.min()) / (cam.max() - cam.min() + 1e-9)

        import cv2

        height, width = prepared.metadata["original_size"]
        heatmap = cv2.resize(cam, (width, height), interpolation=cv2.INTER_LINEAR)
        elapsed_ms = (time.perf_counter() - start) * 1000.0
        return HeatmapResult(heatmap=heatmap, time_ms=round(elapsed_ms, 2))


# ── Overlay + persistence helpers (shared by every provider) ─────────────


def apply_heatmap_overlay(
    original_rgb: np.ndarray,
    heatmap: np.ndarray,
    *,
    opacity: float = 0.5,
) -> np.ndarray:
    """Blend a Jet-coloured heatmap over the original RGB image.

    ``opacity`` is clamped to ``[0, 1]`` (0 = original only, 1 = heatmap only).
    The heatmap is resized to the original dimensions when needed so the output
    is always full-resolution (high-res export).
    """
    import cv2

    opacity = float(np.clip(opacity, 0.0, 1.0))
    height, width = original_rgb.shape[:2]
    heat: np.ndarray = np.clip(heatmap.astype(np.float32), 0.0, 1.0)
    if heat.shape[:2] != (height, width):
        heat = cv2.resize(heat, (width, height), interpolation=cv2.INTER_LINEAR)
    heat_bgr = cv2.applyColorMap((heat * 255.0).astype(np.uint8), cv2.COLORMAP_JET)
    original_bgr = cv2.cvtColor(original_rgb, cv2.COLOR_RGB2BGR)
    overlay_bgr = cv2.addWeighted(heat_bgr, opacity, original_bgr, 1.0 - opacity, 0)
    return cv2.cvtColor(overlay_bgr, cv2.COLOR_BGR2RGB)


def encode_heatmap_png(heatmap: np.ndarray) -> bytes:
    """Encode a normalized heatmap as a lossless grayscale PNG."""
    import cv2

    gray = (np.clip(heatmap, 0.0, 1.0) * 255.0).astype(np.uint8)
    ok, buf = cv2.imencode(".png", gray)
    if not ok:
        raise ImageValidationError("failed to encode heatmap PNG")
    return buf.tobytes()


def decode_heatmap_png(data: bytes) -> np.ndarray:
    """Decode a grayscale heatmap PNG back to a float32 ``[0, 1]`` map."""
    import cv2

    buffer = np.frombuffer(data, dtype=np.uint8)
    gray = cv2.imdecode(buffer, cv2.IMREAD_GRAYSCALE)
    if gray is None:
        raise ImageValidationError("failed to decode heatmap PNG")
    return gray.astype(np.float32) / 255.0


def encode_rgb_png(rgb: np.ndarray) -> bytes:
    """Encode an RGB uint8 array as a PNG byte blob."""
    import cv2

    ok, buf = cv2.imencode(".png", cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR))
    if not ok:
        raise ImageValidationError("failed to encode overlay PNG")
    return buf.tobytes()
