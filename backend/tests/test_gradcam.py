"""Unit tests for the Grad-CAM explainability core (M2, Task 5).

Covers heatmap validity (shape, range, determinism), the OpenCV overlay +
PNG encode/decode helpers, the TensorFlow provider's graceful degradation
without a CNN available, and loose performance budgets for the CPU path.
"""

import time
from io import BytesIO
from typing import cast

import numpy as np
import pytest
from app.ai.gradcam import (
    RuleBaselineSaliency,
    TensorFlowGradCAM,
    apply_heatmap_overlay,
    decode_heatmap_png,
    encode_heatmap_png,
    encode_rgb_png,
)
from app.ai.preprocess import Preprocessor
from app.ai.types import ImageData, InferenceError
from PIL import Image


def _image(width: int = 224, height: int = 224, seed: int = 0) -> ImageData:
    """A textured image with a bright lesion-like blob (real edge energy)."""
    rng = np.random.default_rng(seed)
    base = np.zeros((height, width, 3), dtype=np.uint8)
    base[..., 0] = np.linspace(0, 255, width, dtype=np.uint8)[None, :]
    base[60:140, 140:220] = rng.integers(100, 255, (80, 80, 3), dtype=np.uint8)
    buf = BytesIO()
    Image.fromarray(base).save(buf, format="JPEG")
    return ImageData(image_bytes=buf.getvalue(), content_type="image/jpeg")


# ── RuleBaselineSaliency ────────────────────────────────────────────────


def test_saliency_heatmap_shape_and_range():
    img = _image()
    result = RuleBaselineSaliency().heatmap(img)
    assert result.heatmap.shape == (224, 224)
    assert result.heatmap.dtype == np.float32
    assert result.heatmap.min() >= 0.0
    assert result.heatmap.max() <= 1.0
    assert result.time_ms > 0.0


def test_saliency_is_deterministic():
    prov = RuleBaselineSaliency()
    first = prov.heatmap(_image(seed=3))
    second = prov.heatmap(_image(seed=3))
    assert np.array_equal(first.heatmap, second.heatmap)


def test_saliency_different_inputs_differ():
    prov = RuleBaselineSaliency()
    a = prov.heatmap(_image(seed=1)).heatmap
    b = prov.heatmap(_image(seed=2)).heatmap
    assert not np.array_equal(a, b)


def test_saliency_returns_original_size():
    img = _image(width=320, height=180)
    assert RuleBaselineSaliency().heatmap(img).heatmap.shape == (180, 320)


# ── PNG round-trip ───────────────────────────────────────────────────────


def test_heatmap_png_roundtrip_is_lossless():
    heat = RuleBaselineSaliency().heatmap(_image()).heatmap
    restored = decode_heatmap_png(encode_heatmap_png(heat))
    assert restored.shape == heat.shape
    assert restored.dtype == np.float32
    # Grayscale PNG is lossless; quantization is the only delta.
    assert np.max(np.abs(restored - heat)) <= 1.0 / 255.0


def test_rgb_png_encodes():
    rgb = np.zeros((64, 64, 3), dtype=np.uint8)
    rgb[..., 2] = 255
    data = encode_rgb_png(rgb)
    assert data.startswith(b"\x89PNG")
    assert len(data) > 0


# ── Overlay helper ──────────────────────────────────────────────────────


def test_overlay_at_zero_opacity_equals_original():
    original = np.zeros((224, 224, 3), dtype=np.uint8)
    original[..., 0] = 200
    heat = RuleBaselineSaliency().heatmap(_image()).heatmap
    out = apply_heatmap_overlay(original, heat, opacity=0.0)
    assert out.dtype == np.uint8
    assert out.shape == original.shape
    assert np.array_equal(out, original)


def test_overlay_at_full_opacity_differs_and_is_colored():
    original = np.zeros((224, 224, 3), dtype=np.uint8)
    heat = RuleBaselineSaliency().heatmap(_image()).heatmap
    out = apply_heatmap_overlay(original, heat, opacity=1.0)
    assert not np.array_equal(out, original)
    # The Jet map is strongly saturated somewhere (a hot region is present).
    assert int(np.max(out.max(axis=2) - out.min(axis=2))) >= 200
    # And a cold (low-heat) corner should stay dark, not original-white.
    assert int(out[0, 0].max()) <= 160


def test_overlay_resizes_heatmap_to_original():
    original = np.zeros((300, 400, 3), dtype=np.uint8)  # high-res target
    heat = np.zeros((224, 224), dtype=np.float32)
    heat[100:150, 100:150] = 1.0
    out = apply_heatmap_overlay(original, heat, opacity=0.5)
    assert out.shape == (300, 400, 3)


def test_overlay_clamps_opacity():
    original = np.zeros((224, 224, 3), dtype=np.uint8)
    heat = RuleBaselineSaliency().heatmap(_image()).heatmap
    assert np.array_equal(
        apply_heatmap_overlay(original, heat, opacity=1.5),
        apply_heatmap_overlay(original, heat, opacity=1.0),
    )
    assert np.array_equal(
        apply_heatmap_overlay(original, heat, opacity=-1.0),
        apply_heatmap_overlay(original, heat, opacity=0.0),
    )


# ── TensorFlowGradCAM (graceful without TF) ─────────────────────────────


def test_tf_gradcam_missing_tensorflow_raises_inference_error():
    provider = TensorFlowGradCAM(
        model=object(),
        preprocessor=cast(Preprocessor, object()),
        label_map={"Late Blight": 0},
        layer_name="conv1",  # explicit layer → __init__ never imports TF
    )
    with pytest.raises(InferenceError, match="tensorflow"):
        provider.heatmap(_image(), "Late Blight")


def test_tf_gradcam_picks_last_conv_layer_with_tf():
    pytest.importorskip("tensorflow")
    import tensorflow as tf

    model = tf.keras.Sequential(
        [
            tf.keras.layers.Input(shape=(32, 32, 3)),
            tf.keras.layers.Conv2D(4, 3, activation="relu", name="conv_a"),
            tf.keras.layers.Conv2D(8, 3, activation="relu", name="conv_b"),
        ]
    )
    assert TensorFlowGradCAM._pick_conv_layer(model) == "conv_b"


# ── Performance budgets (CPU path) ──────────────────────────────────────


def test_saliency_heatmap_within_time_budget():
    img = _image()
    start = time.perf_counter()
    RuleBaselineSaliency().heatmap(img)
    assert time.perf_counter() - start < 1.0


def test_overlay_render_within_time_budget():
    heat = RuleBaselineSaliency().heatmap(_image()).heatmap
    original = np.zeros((640, 480, 3), dtype=np.uint8)  # high-res export target
    start = time.perf_counter()
    apply_heatmap_overlay(original, heat, opacity=0.5)
    assert time.perf_counter() - start < 1.0
