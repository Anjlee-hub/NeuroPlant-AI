"""OpenCV-backed preprocessing pipeline (M2, Task 3).

The provider validates, decodes, EXIF-strips, resizes/pads, and normalizes an
uploaded image into a deterministic model-ready tensor, and additionally
sanitizes images for storage and augments images for training.

Security & robustness (all verified by unit tests):

- magic-byte validation (never trusts file extensions or declared MIME alone)
- MIME allowlist
- maximum file size
- maximum / minimum dimension guards
- decompression-bomb protection via Pillow's ``MAX_IMAGE_PIXELS`` guard
- EXIF orientation applied once, then EXIF metadata stripped for storage
- corruption rejected at decode time

Performance notes for low-end Android clients: the heavy work runs in cv2
(C-accelerated) with a small (224px) square target, `INTER_AREA` downsampling,
zero unnecessary array copies (``np.ascontiguousarray`` only where needed) and
no Pillow→array round-trips beyond the initial decode. ``preprocess`` is
deterministic — no RNG — and ``augment`` is only ever called by training code.

Explainability preparation (Task 5): :meth:`prepare` returns a
:class:`PreprocessResult` carrying the original image, the aspect-preserving
resize, the padded model-input image, and the normalized tensor, plus metadata
(the input size, channel order, normalization and original dims) needed to
build a Grad-CAM heatmap later.
"""

from __future__ import annotations

import time
from io import BytesIO

import numpy as np
from PIL import Image, ImageOps, UnidentifiedImageError

from app.ai.preprocess import (
    ImageValidationError,
    PreprocessResult,
    register_preprocessor,
)
from app.ai.types import ImageData
from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# Bump when the normalization / layout of the tensor changes.
PREPROCESS_VERSION = "cv2-v1"

# Content types we accept, keyed by MIME → leading magic signatures.
_MAGIC: dict[str, tuple[bytes, ...]] = {
    "image/jpeg": (b"\xff\xd8\xff",),
    "image/png": (b"\x89PNG\r\n\x1a\n",),
    "image/webp": (b"RIFF",),  # needs the WEBP marker at offset 8 (see below)
    "image/bmp": (b"BM",),
    "image/gif": (b"GIF87a", b"GIF89a"),
    "image/tiff": (b"II*\x00", b"MM\x00*"),
}


def _matches_magic(data: bytes, content_type: str) -> bool:
    if content_type == "image/webp":
        return data.startswith(b"RIFF") and data[8:12] == b"WEBP"
    return any(data.startswith(sig) for sig in _MAGIC[content_type])


class OpenCVPreprocessor:
    """Default cv2-backed :class:`Preprocessor` (validate / prepare / augment)."""

    def __init__(
        self,
        *,
        max_bytes: int = 15 * 1024 * 1024,
        max_dimension: int = 8000,
        min_dimension: int = 16,
        target_size: int = 224,
        jpeg_quality: int = 92,
    ) -> None:
        # cv2 is an M2+ dependency; import lazily so the base install works.
        try:
            import cv2
        except ImportError as exc:  # pragma: no cover - exercised in CI envs
            raise ImageValidationError(
                "opencv-python-headless is not installed (pip install -r requirements-ml.txt)"
            ) from exc
        self._cv2 = cv2
        self._max_bytes = max_bytes
        self._max_dimension = max_dimension
        self._max_pixels = max_dimension * max_dimension
        self._min_dimension = min_dimension
        self._target_size = target_size
        self._jpeg_quality = jpeg_quality

    # ── Validation ──────────────────────────────────────────────────────

    def validate(self, image: ImageData) -> ImageData:
        """Cheap pre-checks only (no decode): MIME + magic + file size."""
        self._check_magic_and_type(image)
        self._check_size(image)
        return image

    def _check_magic_and_type(self, image: ImageData) -> None:
        content_type = (image.content_type or "").split(";")[0].strip().lower()
        if content_type not in _MAGIC:
            raise ImageValidationError(f"unsupported content type: {image.content_type!r}")
        if not _matches_magic(image.image_bytes, content_type):
            raise ImageValidationError("file content does not match declared content type")

    def _check_size(self, image: ImageData) -> None:
        size = len(image.image_bytes)
        if size > self._max_bytes:
            raise ImageValidationError(f"file too large: {size} bytes (max {self._max_bytes})")

    # ── Decode (bomb-safe, EXIF orientation applied, EXIF not carried) ──

    def _decode(self, data: bytes) -> np.ndarray:
        # Pillow refuses to materialize images above the pixel budget, which is
        # the defence against decompression bombs regardless of file size.
        Image.MAX_IMAGE_PIXELS = self._max_pixels
        try:
            with Image.open(BytesIO(data)) as pil:
                pil.load()
                oriented = ImageOps.exif_transpose(pil)  # bake camera orientation
                arr = np.asarray(oriented.convert("RGB"), dtype=np.uint8)
        except Image.DecompressionBombError as exc:
            raise ImageValidationError(
                "image exceeds maximum pixel dimensions (decompression bomb)"
            ) from exc
        except (UnidentifiedImageError, OSError, ValueError, SyntaxError) as exc:
            raise ImageValidationError(f"unable to decode image: {exc}") from exc
        return np.ascontiguousarray(arr)

    # ── Inference pipeline (deterministic, never augments) ──────────────

    def prepare(self, image: ImageData) -> PreprocessResult:
        self.validate(image)
        original = self._decode(image.image_bytes)
        height, width = original.shape[:2]
        if max(height, width) > self._max_dimension:
            raise ImageValidationError(
                f"image too large: {width}x{height} (max side {self._max_dimension})"
            )
        if min(height, width) < self._min_dimension:
            raise ImageValidationError(
                f"image too small: {width}x{height} (min side {self._min_dimension})"
            )
        resized, padded = self._resize_and_pad(original, self._target_size)
        tensor = padded.astype(np.float32) / 255.0
        metadata = {
            "preprocessor_version": PREPROCESS_VERSION,
            "original_size": (height, width),
            "resized_size": (resized.shape[0], resized.shape[1]),
            "input_size": (self._target_size, self._target_size),
            "channel_order": "RGB",
            "normalization": "divide-255",
            "dtype": str(tensor.dtype),
        }
        logger.debug(
            "image_preprocessed",
            width=width,
            height=height,
            tensor=str(tensor.shape),
        )
        return PreprocessResult(
            tensor=tensor,
            image=padded,
            resized=resized,
            original=original,
            metadata=metadata,
        )

    def preprocess(self, image: ImageData) -> np.ndarray:
        """Model-ready tensor only (what the classifier consumes)."""
        return self.prepare(image).tensor

    def sanitize(self, image: ImageData) -> ImageData:
        """Re-encode as clean JPEG with EXIF fully stripped (storage-safe)."""
        self.validate(image)
        arr = self._decode(image.image_bytes)
        ok, buf = self._cv2.imencode(
            ".jpg",
            arr[:, :, ::-1],  # cv2 wants BGR
            [self._cv2.IMWRITE_JPEG_QUALITY, self._jpeg_quality],
        )
        if not ok:
            raise ImageValidationError("failed to re-encode sanitized image")
        return ImageData(
            image_bytes=buf.tobytes(),
            content_type="image/jpeg",
            width=arr.shape[1],
            height=arr.shape[0],
            source_type=image.source_type,
        )

    def _resize_and_pad(self, img: np.ndarray, target: int) -> tuple[np.ndarray, np.ndarray]:
        """Aspect-ratio-preserving resize to fit ``target``, centered black pad."""
        cv2 = self._cv2
        height, width = img.shape[:2]
        scale = target / max(height, width)
        new_w = max(1, int(round(width * scale)))
        new_h = max(1, int(round(height * scale)))
        interpolation = cv2.INTER_AREA if scale < 1.0 else cv2.INTER_LINEAR
        resized = cv2.resize(img, (new_w, new_h), interpolation=interpolation)
        top = (target - new_h) // 2
        bottom = target - new_h - top
        left = (target - new_w) // 2
        right = target - new_w - left
        padded = cv2.copyMakeBorder(
            resized, top, bottom, left, right, cv2.BORDER_CONSTANT, value=(0, 0, 0)
        )
        return resized, padded

    # ── Augmentation (training / TTA only — never in inference) ─────────

    def augment(
        self,
        image: ImageData,
        *,
        count: int = 4,
        seed: int | None = None,
    ) -> list[ImageData]:
        """Return ``count`` randomized training variants, re-encoded as JPEG.

        A seed yields reproducible variants (used by tests and offline
        augmentation jobs).
        """
        self.validate(image)
        base = self._decode(image.image_bytes)
        rng = np.random.default_rng(seed)
        variants: list[ImageData] = []
        for _ in range(count):
            variant = self._random_crop_zoom(base, rng)
            variant = self._random_rotate(variant, rng)
            variant = self._random_flip(variant, rng)
            variant = self._random_brightness_contrast(variant, rng)
            variant = self._random_color_jitter(variant, rng)
            variant = self._random_noise(variant, rng)
            variants.append(self._encode_jpeg(variant))
        return variants

    def _encode_jpeg(self, rgb: np.ndarray) -> ImageData:
        ok, buf = self._cv2.imencode(
            ".jpg",
            rgb[:, :, ::-1],  # cv2 wants BGR
            [self._cv2.IMWRITE_JPEG_QUALITY, self._jpeg_quality],
        )
        if not ok:
            raise ImageValidationError("failed to encode augmented image")
        return ImageData(
            image_bytes=buf.tobytes(),
            content_type="image/jpeg",
            width=rgb.shape[1],
            height=rgb.shape[0],
        )

    def _random_crop_zoom(self, arr: np.ndarray, rng: np.random.Generator) -> np.ndarray:
        """Random crop (85–100% area) resized back to full size = zoom-in."""
        height, width = arr.shape[:2]
        fraction = float(rng.uniform(0.85, 1.0))
        ch = max(16, int(height * fraction))
        cw = max(16, int(width * fraction))
        y0 = int(rng.integers(0, max(1, height - ch + 1)))
        x0 = int(rng.integers(0, max(1, width - cw + 1)))
        crop = arr[y0 : y0 + ch, x0 : x0 + cw]
        return self._cv2.resize(crop, (width, height), interpolation=self._cv2.INTER_LINEAR)

    def _random_rotate(self, arr: np.ndarray, rng: np.random.Generator) -> np.ndarray:
        angle = float(rng.uniform(-15.0, 15.0))
        if abs(angle) < 0.5:
            return arr
        height, width = arr.shape[:2]
        matrix = self._cv2.getRotationMatrix2D((width / 2, height / 2), angle, 1.0)
        return self._cv2.warpAffine(
            arr,
            matrix,
            (width, height),
            flags=self._cv2.INTER_LINEAR,
            borderMode=self._cv2.BORDER_REFLECT_101,
        )

    def _random_flip(self, arr: np.ndarray, rng: np.random.Generator) -> np.ndarray:
        if rng.random() < 0.5:
            arr = self._cv2.flip(arr, 1)  # horizontal
        if rng.random() < 0.5:
            arr = self._cv2.flip(arr, 0)  # vertical
        return arr

    def _random_brightness_contrast(self, arr: np.ndarray, rng: np.random.Generator) -> np.ndarray:
        contrast = float(rng.uniform(0.8, 1.2))
        brightness = float(rng.uniform(-30.0, 30.0))
        return self._cv2.convertScaleAbs(arr, alpha=contrast, beta=brightness)

    def _random_color_jitter(self, arr: np.ndarray, rng: np.random.Generator) -> np.ndarray:
        if rng.random() >= 0.8:
            return arr
        hsv = self._cv2.cvtColor(arr, self._cv2.COLOR_RGB2HSV).astype(np.float32)
        hue = float(rng.uniform(-10.0, 10.0))
        hsv[..., 0] = (hsv[..., 0] + hue) % 180.0
        hsv[..., 1] = np.clip(hsv[..., 1] * float(rng.uniform(0.8, 1.2)), 0, 255)
        return self._cv2.cvtColor(hsv.astype(np.uint8), self._cv2.COLOR_HSV2RGB)

    def _random_noise(self, arr: np.ndarray, rng: np.random.Generator) -> np.ndarray:
        sigma = float(rng.uniform(0.0, 10.0))
        if sigma <= 0.0:
            return arr
        noise = rng.normal(0.0, sigma, arr.shape).astype(np.float32)
        return np.clip(arr.astype(np.float32) + noise, 0, 255).astype(np.uint8)


# ── Default provider registration (lazy, once per process) ──────────────

_default_preprocessor: OpenCVPreprocessor | None = None


def get_default_preprocessor() -> OpenCVPreprocessor:
    """Build (once) the shared provider from app settings."""
    global _default_preprocessor
    if _default_preprocessor is None:
        settings = get_settings()
        _default_preprocessor = OpenCVPreprocessor(
            max_bytes=settings.preprocess_max_bytes,
            max_dimension=settings.preprocess_max_dimension,
            min_dimension=settings.preprocess_min_dimension,
            target_size=settings.preprocess_target_size,
            jpeg_quality=settings.preprocess_jpeg_quality,
        )
    return _default_preprocessor


def register_default_preprocessor() -> None:
    register_preprocessor("default", get_default_preprocessor())


def benchmark_preprocess(
    preprocessor: OpenCVPreprocessor,
    image: ImageData,
    runs: int = 10,
) -> float:
    """Average wall-clock :meth:`preprocess` time in milliseconds."""
    start = time.perf_counter()
    for _ in range(runs):
        preprocessor.preprocess(image)
    elapsed_ms = (time.perf_counter() - start) * 1000.0 / runs
    return elapsed_ms
