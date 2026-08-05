"""Scan processing pipeline — validate → sanitize → store → detect → persist.

Live uploads (``POST /scans`` multipart) and offline sync items
(``POST /scans/sync`` base64 batch) both funnel through the same internal
representation, :class:`app.ai.types.ImageData`, and the same shared run core
:meth:`ScanPipelineService._process_images`, so validation, preprocessing,
inference, explainability, persistence and error handling are byte-for-byte
identical between the two paths (Task 6.2). Only the raw-input adapters differ
(:meth:`_image_from_upload` vs :meth:`_image_from_sync`).

Failures surface as :class:`ScanPipelineError` subclasses carrying an HTTP
``status_code`` and a machine ``code``; ``main.py`` maps them to the standard
``{"error": {"code", "message"}}`` envelope (and the sync endpoint to a
per-item ``SyncErrorOut``).
"""

from __future__ import annotations

import asyncio
import base64
import time
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime

import numpy as np
from fastapi import UploadFile
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.gradcam import (
    HeatmapResult,
    apply_heatmap_overlay,
    encode_heatmap_png,
    encode_rgb_png,
)
from app.ai.preprocess import ImageValidationError, Preprocessor
from app.ai.types import ImageData, InferenceError
from app.core.logging import get_logger
from app.models.scan import Scan
from app.schemas.scan import ScanCreate, ScanSyncItemIn, SyncImageIn
from app.services.detection import DetectionService, ScanResult, confidence_level
from app.services.scans import ScanService, _now_naive_utc
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
    """Serialize alternate candidates into the ``ai_metadata.rankings`` shape."""
    return [
        {
            "disease_name": rank.disease_name,
            "confidence": rank.confidence,
            "disease_id": rank.disease_id,
            "crop_id": rank.crop_id,
        }
        for rank in result.rankings
    ]


def _top5(result: ScanResult) -> list[dict]:
    """Serialize the ordered top-5 candidates (top-1 + alternates, Task 5.2).

    Stored as ``ai_metadata.top5`` so consumers have the full ranked set with
    per-candidate confidence without re-deriving it from the scan row.
    """
    candidates: list[dict] = [
        {
            "disease_name": result.disease_name,
            "confidence": result.confidence,
            "disease_id": result.disease_id,
            "crop_id": result.crop_id,
        }
    ]
    candidates.extend(_rankings(result))
    return candidates[:5]


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
        """Run one live upload; returns ``(scan, created)``.

        ``created=False`` is an idempotent replay: the ``client_scan_id`` was
        already processed, so the existing row is returned unchanged and the
        endpoint answers 200 instead of 201.

        The multipart files are adapted to :class:`ImageData` and then handed
        to the same shared run core as offline sync items (Task 6.2).
        """
        images = [await self._image_from_upload(upload) for upload in files]
        return await self._process_images(
            user_id=user_id,
            images=images,
            client_scan_id=client_scan_id,
            crop_id=crop_id,
            part_type=part_type,
            device_id=device_id,
            source_type="upload",
        )

    async def process_sync_item(
        self,
        *,
        user_id: int,
        item: ScanSyncItemIn,
    ) -> tuple[Scan, bool]:
        """Run one queued offline scan; returns ``(scan, created)``.

        Base64 images are decoded and adapted to :class:`ImageData`, then the
        *identical* pipeline as a live upload runs — validation, preprocessing,
        inference, explainability, persistence and error handling are shared.
        Rows created here carry ``source_type="sync"`` on their media items and
        a ``synced_at`` stamp (``created=False`` is an idempotent replay, same
        as ``POST /scans``).
        """
        images = [self._image_from_sync(image) for image in item.images]
        return await self._process_images(
            user_id=user_id,
            images=images,
            client_scan_id=item.client_scan_id,
            crop_id=item.crop_id,
            part_type=item.part_type,
            device_id=item.device_id,
            source_type="sync",
            synced_at=_now_naive_utc(),
        )

    async def _process_images(
        self,
        *,
        user_id: int,
        images: Sequence[ImageData],
        client_scan_id: str,
        crop_id: int | None,
        part_type: str | None,
        device_id: str | None,
        source_type: str,
        synced_at: datetime | None = None,
    ) -> tuple[Scan, bool]:
        """The single run core shared by live uploads and offline sync.

        Everything downstream of input adaptation is here — count/idempotency
        checks, validate → sanitize → store, preprocessing, inference, Grad-CAM,
        and persistence — so there is exactly one implementation of the
        detection pipeline and no online/offline drift.
        """
        if not images:
            raise ImageRejectedError("at least one image is required")
        if len(images) > self.max_images:
            raise ImageRejectedError(f"too many images: {len(images)} (max {self.max_images})")

        scans = ScanService(self.db)
        existing = await scans.find_by_client_id(client_scan_id, user_id)
        if existing is not None:
            logger.info("scan_replayed", client_scan_id=client_scan_id, user_id=user_id)
            return existing, False

        started = time.perf_counter()
        stored = [await self._validate_and_store(image, user_id, part_type) for image in images]

        # Preprocessing timing + persisted model-input image (Task 5 Grad-CAM).
        first = stored[0]
        prep_started = time.perf_counter()
        prepared = self.preprocessor.prepare(first.image_data)
        preprocessing_ms = (time.perf_counter() - prep_started) * 1000.0
        processed_key = self._store_processed(prepared.image, user_id)

        result = await self._predict(first.image_data)
        total_ms = (time.perf_counter() - started) * 1000.0

        # Task 5.2 — Grad-CAM: generate + persist the heatmap, best-effort so
        # an explainability failure never fails the diagnosis itself.
        heatmap = await self._heatmap(first.image_data, result.disease_name)
        heatmap_path, grad_cam = self._persist_heatmap(heatmap, prepared.image, result, user_id)

        payload = ScanCreate(
            client_scan_id=client_scan_id,
            user_id=user_id,
            image_path=first.media_item["path"],
            media_items=[image.media_item for image in stored],
            processed_image_path=processed_key,
            heatmap_path=heatmap_path,
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
            ai_metadata={
                "rankings": _rankings(result),
                "top5": _top5(result),
                "confidence": {
                    "top": result.confidence,
                    "level": confidence_level(result.confidence),
                },
                "model": {
                    "provider": result.provider,
                    "model_name": result.model_name,
                    "model_version": result.model_version,
                    "dataset_version": result.dataset_version,
                },
                "grad_cam": grad_cam,
            },
            device_id=device_id,
            synced_at=synced_at,
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

    async def _image_from_upload(self, upload: UploadFile) -> ImageData:
        """Adapt one multipart file into the common internal image type."""
        data = await upload.read()
        content_type = (upload.content_type or "").split(";")[0].strip().lower()
        return ImageData(image_bytes=data, content_type=content_type, source_type="upload")

    def _image_from_sync(self, image: SyncImageIn) -> ImageData:
        """Decode one base64 offline image into the common internal type.

        Raises :class:`ImageRejectedError` (code ``invalid_image``) when the
        payload is not valid base64, so malformed sync items fail the same way
        corrupt uploads do.
        """
        try:
            data = base64.b64decode(image.data.strip(), validate=True)
        except ValueError as exc:
            raise ImageRejectedError(f"invalid base64 image payload: {exc}") from exc
        content_type = (image.content_type or "").split(";")[0].strip().lower()
        return ImageData(image_bytes=data, content_type=content_type, source_type="sync")

    async def _validate_and_store(
        self,
        image: ImageData,
        user_id: int,
        part_type: str | None,
    ) -> UploadedImage:
        """Validate → sanitize (EXIF strip) → store → media item.

        Shared by both input paths — ``image`` is already in the common
        internal representation, and ``image.source_type`` (``upload`` vs
        ``sync``) is recorded on the media item.
        """
        try:
            self.preprocessor.validate(image)
        except ImageValidationError as exc:
            raise _map_validation_error(exc) from exc

        try:
            sanitized = self.preprocessor.sanitize(image)
        except ImageValidationError as exc:
            raise ImageRejectedError(str(exc)) from exc

        try:
            key = self.storage.save(
                sanitized.image_bytes, sanitized.content_type, user_id, subdir="scans"
            )
        except OSError as exc:
            raise StorageFailedError(f"could not store image: {exc}") from exc

        media_item = {
            "source_type": image.source_type,
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

    async def _heatmap(self, image: ImageData, class_name: str) -> HeatmapResult | None:
        """Best-effort Grad-CAM for the predicted class (Task 5.2).

        A failure here (no explainer, timeout, provider error) is logged and
        swallowed — the diagnosis stands and the scan saves without a heatmap.
        """
        try:
            return await asyncio.wait_for(
                self.detection.generate_heatmap_async(image, class_name),
                timeout=self.timeout_seconds,
            )
        except (TimeoutError, InferenceError) as exc:
            logger.warning("heatmap_generation_failed", class_name=class_name, error=str(exc))
            return None

    def _persist_heatmap(
        self,
        heatmap: HeatmapResult | None,
        base_rgb: np.ndarray,
        result: ScanResult,
        user_id: int,
    ) -> tuple[str | None, dict | None]:
        """Store the raw + overlay heatmap PNGs; return ``(path, grad_cam meta)``.

        ``heatmap_path`` (the scan column) points at the overlay — the visual
        artifact the explain endpoint serves — while the raw grayscale map is
        kept in ``ai_metadata.grad_cam`` so it can be re-blended at any opacity
        without re-running inference.
        """
        if heatmap is None:
            return None, None
        raw_key, overlay_key = self._store_heatmap(heatmap.heatmap, base_rgb, user_id)
        explainer = self.detection.explainer
        return overlay_key, {
            "provider": (explainer.provider_name if explainer is not None else "unknown"),
            "class_name": result.disease_name,
            "time_ms": heatmap.time_ms,
            "heatmap_path": raw_key,
            "overlay_path": overlay_key,
        }

    def _store_heatmap(
        self, heatmap: np.ndarray, base_rgb: np.ndarray, user_id: int
    ) -> tuple[str, str]:
        """Persist the raw grayscale map and its Jet overlay over the model input."""
        try:
            raw_key = self.storage.save(
                encode_heatmap_png(heatmap), "image/png", user_id, subdir="heatmaps"
            )
            overlay = apply_heatmap_overlay(base_rgb, heatmap, opacity=0.5)
            overlay_key = self.storage.save(
                encode_rgb_png(overlay), "image/png", user_id, subdir="heatmaps"
            )
        except OSError as exc:
            raise StorageFailedError(f"could not store heatmap: {exc}") from exc
        return raw_key, overlay_key


def _map_validation_error(exc: ImageValidationError) -> ScanPipelineError:
    """Translate preprocessor validation failures to typed pipeline errors."""
    message = str(exc)
    if message.startswith("unsupported content type"):
        return UnsupportedFormatError(message)
    return ImageRejectedError(message)
