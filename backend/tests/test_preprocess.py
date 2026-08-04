"""Unit tests for the OpenCV preprocessing pipeline (M2, Task 3).

Covers image validation (magic bytes, MIME, size, dimensions, corruption,
decompression bombs), EXIF stripping/orientation, deterministic inference
preprocessing, training-only augmentation, and performance sanity checks.
"""

import struct
import zlib
from io import BytesIO

import numpy as np
import pytest
from app.ai.opencv_preprocess import (
    OpenCVPreprocessor,
    benchmark_preprocess,
    get_default_preprocessor,
    register_default_preprocessor,
)
from app.ai.preprocess import ImageValidationError, get_preprocessor
from app.ai.types import ImageData
from PIL import Image

_TARGET = 224


def _image_bytes(
    width: int = 400,
    height: int = 300,
    fmt: str = "JPEG",
    exif_orientation: int | None = None,
    seed: int = 0,
) -> bytes:
    """Build a real encoded image (optionally carrying an EXIF orientation)."""
    arr = np.random.default_rng(seed).integers(0, 256, (height, width, 3), dtype=np.uint8)
    img = Image.fromarray(arr, mode="RGB")
    buf = BytesIO()
    if exif_orientation is not None:
        exif = Image.Exif()
        exif[0x0112] = exif_orientation  # EXIF Orientation tag
        img.save(buf, format="JPEG", exif=exif)
    else:
        img.save(buf, format=fmt)
    return buf.getvalue()


def _jpeg(width: int = 400, height: int = 300, **kw) -> ImageData:
    return ImageData(
        image_bytes=_image_bytes(width=width, height=height, **kw),
        content_type="image/jpeg",
    )


def _prep(**kwargs) -> OpenCVPreprocessor:
    return OpenCVPreprocessor(**kwargs)


def _bomb_png(width: int = 40000, height: int = 40000) -> bytes:
    """A tiny PNG whose declared dimensions are enormous (decompression bomb).

    The pixel-count guard fires in ``Image.open`` before the raster is
    materialized, so the IDAT payload itself never needs to be valid.
    """

    def _chunk(tag: bytes, payload: bytes) -> bytes:
        body = tag + payload
        return (
            struct.pack(">I", len(payload))
            + body
            + struct.pack(">I", zlib.crc32(body) & 0xFFFFFFFF)
        )

    ihdr = struct.pack(">IIBBBBB", width, height, 8, 0, 0, 0, 0)
    idat = zlib.compress(b"\x00" + b"\x00" * (width * 3))  # one black scanline
    return (
        b"\x89PNG\r\n\x1a\n" + _chunk(b"IHDR", ihdr) + _chunk(b"IDAT", idat) + _chunk(b"IEND", b"")
    )


# ── Validation ──────────────────────────────────────────────────────────


def test_validate_accepts_jpeg_and_png():
    prep = _prep()
    assert prep.validate(_jpeg()) is not None
    png = ImageData(image_bytes=_image_bytes(fmt="PNG"), content_type="image/png")
    assert prep.validate(png) is not None


def test_validate_rejects_unknown_content_type():
    with pytest.raises(ImageValidationError, match="unsupported content type"):
        _prep().validate(ImageData(image_bytes=_image_bytes(), content_type="image/heic"))


def test_validate_rejects_magic_mismatch():
    # Real PNG bytes labelled as JPEG -> content/type mismatch, not trust ext.
    with pytest.raises(ImageValidationError, match="does not match"):
        _prep().validate(ImageData(image_bytes=_image_bytes(fmt="PNG"), content_type="image/jpeg"))


def test_validate_rejects_oversized_file():
    small = OpenCVPreprocessor(max_bytes=100)
    with pytest.raises(ImageValidationError, match="too large"):
        small.validate(_jpeg())


def test_prepare_rejects_corrupt_bytes():
    # Valid JPEG magic but garbage payload -> passes cheap checks, fails decode.
    corrupt = ImageData(image_bytes=b"\xff\xd8\xff" + b"\x00" * 64, content_type="image/jpeg")
    with pytest.raises(ImageValidationError, match="unable to decode"):
        _prep().prepare(corrupt)


def test_prepare_rejects_large_dimensions():
    # max_dimension=600 keeps the pixel budget (360k) above this image (307k)
    # so the dimension guard — not the decompression-bomb guard — fires.
    with pytest.raises(ImageValidationError, match="image too large"):
        OpenCVPreprocessor(max_dimension=600).prepare(_jpeg(width=640, height=480))


def test_prepare_rejects_tiny_images():
    with pytest.raises(ImageValidationError, match="too small"):
        _prep().prepare(_jpeg(width=8, height=8))


def test_prepare_rejects_decompression_bomb():
    bomb = ImageData(image_bytes=_bomb_png(), content_type="image/png")
    with pytest.raises(ImageValidationError, match="decompression bomb"):
        _prep().prepare(bomb)


# ── EXIF stripping & orientation ────────────────────────────────────────


def test_exif_orientation_applied_then_stripped():
    prep = _prep()
    stored = _jpeg(width=400, height=300, exif_orientation=6)
    result = prep.prepare(stored)
    # Orientation 6 (90° CW display) swaps the decoded H/W vs the stored file.
    assert result.original.shape[:2] == (400, 300)
    # Control: no EXIF -> no transpose.
    plain = prep.prepare(_jpeg(width=400, height=300))
    assert plain.original.shape[:2] == (300, 400)
    # Sanitized output carries no EXIF at all.
    clean = prep.sanitize(stored)
    with Image.open(BytesIO(clean.image_bytes)) as img:
        assert len(img.getexif()) == 0


def test_sanitize_returns_stripped_jpeg_with_dimensions():
    clean = _prep().sanitize(_jpeg(exif_orientation=3))
    assert clean.content_type == "image/jpeg"
    assert (clean.width, clean.height) == (400, 300)
    with Image.open(BytesIO(clean.image_bytes)) as img:
        assert len(img.getexif()) == 0


# ── Inference preprocessing (deterministic) ─────────────────────────────


def test_prepare_returns_correct_shapes_and_range():
    result = _prep().prepare(_jpeg(width=640, height=480))
    assert result.tensor.shape == (_TARGET, _TARGET, 3)
    assert result.tensor.dtype == np.float32
    assert result.tensor.min() >= 0.0
    assert result.tensor.max() <= 1.0
    assert result.image.shape == (_TARGET, _TARGET, 3)
    assert result.image.dtype == np.uint8
    assert result.original.shape == (480, 640, 3)
    # Aspect ratio preserved: resized keeps 4:3, longest side == target.
    h, w = result.resized.shape[:2]
    assert max(h, w) == _TARGET
    assert min(h, w) < _TARGET
    assert result.metadata["channel_order"] == "RGB"
    assert result.metadata["original_size"] == (480, 640)


def test_preprocess_is_deterministic():
    img = _jpeg()
    prep = _prep()
    first = prep.prepare(img)
    second = prep.prepare(img)
    assert np.array_equal(first.tensor, second.tensor)
    assert np.array_equal(first.image, second.image)
    assert np.array_equal(first.original, second.original)


def test_preprocess_returns_tensor_matching_prepare():
    img = _jpeg()
    prep = _prep()
    assert np.array_equal(prep.preprocess(img), prep.prepare(img).tensor)


# ── Augmentation (training only, never in inference) ────────────────────


def test_augment_returns_valid_same_size_variants():
    variants = _prep().augment(_jpeg(), count=4, seed=7)
    assert len(variants) == 4
    for variant in variants:
        assert variant.content_type == "image/jpeg"
        with Image.open(BytesIO(variant.image_bytes)) as img:
            assert img.size == (400, 300)


def test_augment_is_seeded_and_changes_content():
    prep = _prep()
    img = _jpeg()
    a = prep.augment(img, count=2, seed=3)
    b = prep.augment(img, count=2, seed=3)
    assert [v.image_bytes for v in a] == [v.image_bytes for v in b]
    base = prep.prepare(img).original
    max_diff = max(np.abs(prep.prepare(v).original.astype(int) - base.astype(int)).max() for v in a)
    # Crop/rotate/flip perturb pixels well beyond JPEG-roundtrip noise.
    assert max_diff > 10


def test_preprocess_never_invokes_augment():
    prep = _prep()
    img = _jpeg()

    def boom(*args, **kwargs):
        raise AssertionError("augment must never run during inference")

    prep.augment = boom  # type: ignore[method-assign]
    prep.preprocess(img)  # must succeed without touching augment


# ── Default provider wiring ─────────────────────────────────────────────


def test_default_preprocessor_available_via_registry():
    # Other tests may have left a stub under "default"; force the real one.
    register_default_preprocessor()
    prep = get_preprocessor("default")
    assert isinstance(prep, OpenCVPreprocessor)
    assert prep is get_default_preprocessor()
    assert prep.prepare(_jpeg()).tensor.shape == (_TARGET, _TARGET, 3)


# ── Performance sanity ──────────────────────────────────────────────────


def test_preprocess_performance_sanity():
    img = _jpeg(width=2048, height=1536)
    prep = _prep()
    avg_ms = benchmark_preprocess(prep, img, runs=5)
    assert avg_ms < 2000.0, f"preprocess too slow: {avg_ms:.1f}ms"
    assert prep.prepare(img).tensor.shape == (_TARGET, _TARGET, 3)
