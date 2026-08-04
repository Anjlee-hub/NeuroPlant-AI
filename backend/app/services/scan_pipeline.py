"""Scan upload pipeline — validate → sanitize → store → detect → persist.

``POST /scans`` composes this service: it owns the ordering and timing of every
stage so the endpoint stays thin and each stage (preprocessor, storage,
detection, scan persistence) stays independently swappable and testable.

Failures surface as :class:`ScanPipelineError` subclasses carrying an HTTP
``status_code`` and a machine ``code``; ``main.py`` maps them to the standard
``{"error": {"code", "message"}}`` envelope.
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Sequence
from dataclasses import dataclass

from fastapi import UploadFile
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.preprocess import ImageValidationError, Preprocessor
from app.ai.types import ImageData, InferenceError
from app.core.logging import get_logger
from app.models.scan import Scan
from app.schemas.scan import ScanCreate
from app.services.detection import DetectionService, ScanResult
from app.services.scans import ScanService
from app.services.storage import StorageService

logger = get_logger(__name__)


class ScanPipelineError(Exception):
    """Base failure for the scan pipeline; maps to a structured HTTP response."""

    code = "scan_pipeline_error"
    status_code = 400


class ImageRejectedError(ScanPipelineError):
    """Bad / corrupt / malicious image (magic, size, decode, dimensions)."""

    code = "invalid_image"
    status_code = 400


class UnsupportedFormatError(ScanPipelineError):
    """Declared MIME is not on the allowlist (never a JPEG/PNG/WebP client)."""

    code = "unsupported_format"
    status_code = 415


class InferenceFailedError(ScanPipelineError):
    """The AI layer failed (unavailable model, prediction error)."""

    code = "inference_failed"
    status_code = 502


class ScanTimeoutError(ScanPipelineError):
    """Inference exceeded the configured ceiling."""

    code = "timeout"
    status_code = 504


class StorageFailedError(ScanPipelineError):
    """Image could not be persisted (disk/object-store failure)."""

    code = "storage_failure"
    status_code = 503


class DuplicateScanError(ScanPipelineError):
    """client_scan_id collided with an existing row (race edge case)."""

    code = "duplicate_client_scan_id"
    status_code = 409


@dataclass(frozen=True)
class UploadedImage:
    """One validated + stored image, ready for the classifier."""

    media_item: dict
    image_data: ImageData  # sanitized (EXIF-stripped) bytes for detection


def _rankings(result: ScanResult) -> list[dict]:
    """Serialize top-k candidates into the ``ai_metadata.rankings`` shape."""
    return [
        {
            "disease_name": rank.disease_name,
            "confidence": rank.confidence,
            "disease_id": rank.disease_id,
            "crop_id": rank.crop_id,
        }
        for rank in result.rankings
    ]


class ScanPipelineService:
    """Orchestrates one scan upload through the full detection pipeline."""

    def __init__(
        self,
        db: AsyncSession,
        detection: DetectionService,
        storage: StorageService,
        preprocessor: Preprocessor,
        *,
        max_images: int = 5,
        timeout_seconds: float = 30.0,
    ) -> None:
        self.db = db
        self.detection = detection
        self.storage = storage
        self.preprocessor = preprocessor
        self.max_images = max_images
        self.timeout_seconds = timeout_seconds

    async def process_upload(
        self,
        *,
        user_id: int,
        files: Sequence[UploadFile],
        client_scan_id: str,
        crop_id: int | None = None,
        part_type: str | None = None,
        device_id: str | None = None,
    ) -> tuple[Scan, bool]:
        """Run one upload; returns ``(scan, created)``.

        ``created=False`` is an idempotent replay: the ``client_scan_id`` was
        already processed, so the existing row is returned unchanged and the
        endpoint answers 200 instead of 201.
        """
        if not files:
            raise ImageRejectedError("at least one image file is required")
        if len(files) > self.max_images:
            raise ImageRejectedError(f"too many images: {len(files)} (max {self.max_images})")

        scans = ScanService(self.db)
        existing = await scans.find_by_client_id(client_scan_id, user_id)
        if existing is not None:
            logger.info("scan_replayed", client_scan_id=client_scan_id, user_id=user_id)
            return existing, False

        started = time.perf_counter()
        images = [await self._validate_and_store(upload, user_id, part_type) for upload in files]

        # Preprocessing timing + persisted model-input image (Task 5 Grad-CAM).
        first = images[0]
        prep_started = time.perf_counter()
        prepared = self.preprocessor.prepare(first.image_data)
        preprocessing_ms = (time.perf_counter() - prep_started) * 1000.0
        processed_key = self._store_processed(prepared.image, user_id)

        result = await self._predict(first.image_data)
        total_ms = (time.perf_counter() - started) * 1000.0

        payload = ScanCreate(
            client_scan_id=client_scan_id,
            user_id=user_id,
            image_path=first.media_item["path"],
            media_items=[image.media_item for image in images],
            processed_image_path=processed_key,
            crop_id=crop_id,
            part_type=part_type,
            disease_id=result.disease_id,
            disease_name=result.disease_name,
            confidence=result.confidence,
            severity=result.severity,
            stage=result.stage,
            provider=result.provider,
            model_name=result.model_name,
            model_version=result.model_version,
            dataset_version=result.dataset_version,
            preprocessing_time_ms=round(preprocessing_ms, 1),
            inference_time_ms=result.inference_time_ms,
            processing_time_ms=round(total_ms, 1),
            ai_metadata={"rankings": _rankings(result)},
            device_id=device_id,
        )
        try:
            scan = await scans.create(payload)
        except IntegrityError:
            # Lost a race on the unique client_scan_id — treat as a replay.
            await self.db.rollback()
            existing = await scans.find_by_client_id(client_scan_id, user_id)
            if existing is not None:
                return existing, False
            raise DuplicateScanError("client_scan_id conflicts with an existing scan") from None
        return scan, True

    # ── Stages ───────────────────────────────────────────────────────────

    async def _validate_and_store(
        self,
        upload: UploadFile,
        user_id: int,
        part_type: str | None,
    ) -> UploadedImage:
        """Read → validate → sanitize (EXIF strip) → store → media item."""
        data = await upload.read()
        content_type = (upload.content_type or "").split(";")[0].strip().lower()
        source = ImageData(image_bytes=data, content_type=content_type, source_type="upload")

        try:
            self.preprocessor.validate(source)
        except ImageValidationError as exc:
            raise _map_validation_error(exc) from exc

        try:
            sanitized = self.preprocessor.sanitize(source)
        except ImageValidationError as exc:
            raise ImageRejectedError(str(exc)) from exc

        try:
            key = self.storage.save(
                sanitized.image_bytes, sanitized.content_type, user_id, subdir="scans"
            )
        except OSError as exc:
            raise StorageFailedError(f"could not store image: {exc}") from exc

        media_item = {
            "source_type": "upload",
            "path": key,
            "url": self.storage.url(key),
            "part_type": part_type,
            "width": sanitized.width,
            "height": sanitized.height,
            "content_type": sanitized.content_type,
        }
        return UploadedImage(media_item=media_item, image_data=sanitized)

    def _store_processed(self, padded_rgb, user_id: int) -> str:
        """Persist the padded model-input image for explainability (Task 5)."""
        jpeg = self.preprocessor.encode_jpeg(padded_rgb)
        try:
            return self.storage.save(
                jpeg.image_bytes, jpeg.content_type, user_id, subdir="processed"
            )
        except OSError as exc:
            raise StorageFailedError(f"could not store processed image: {exc}") from exc

    async def _predict(self, image: ImageData) -> ScanResult:
        """Run inference in a worker thread under a hard timeout."""
        try:
            return await asyncio.wait_for(
                self.detection.predict_async(image), timeout=self.timeout_seconds
            )
        except TimeoutError:
            raise ScanTimeoutError("AI inference exceeded the time limit") from None
        except InferenceError as exc:
            raise InferenceFailedError(str(exc)) from exc


def _map_validation_error(exc: ImageValidationError) -> ScanPipelineError:
    """Translate preprocessor validation failures to typed pipeline errors."""
    message = str(exc)
    if message.startswith("unsupported content type"):
        return UnsupportedFormatError(message)
    return ImageRejectedError(message)
