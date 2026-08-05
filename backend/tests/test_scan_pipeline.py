"""Service-level tests for the scan upload pipeline (M2, Task 4.2).

The pipeline is exercised with a stub detector (deterministic ScanResult) so
the tests cover validation → sanitize → storage → timing → persistence and the
error mapping without needing an AI artifact. API-level behaviour (auth, status
codes, idempotency over HTTP) is covered in test_scan_api.py.
"""

import asyncio
import base64
import uuid
from io import BytesIO

import numpy as np
import pytest
from app.ai.gradcam import HeatmapResult
from app.ai.opencv_preprocess import OpenCVPreprocessor
from app.ai.types import InferenceError, PredictedDisease
from app.schemas.scan import ScanSyncItemIn, SyncImageIn
from app.services.detection import ScanResult
from app.services.scan_pipeline import (
    ImageRejectedError,
    InferenceFailedError,
    ScanPipelineService,
    ScanTimeoutError,
    StorageFailedError,
    UnsupportedFormatError,
)
from app.services.storage import LocalStorageService
from fastapi import UploadFile
from PIL import Image
from starlette.datastructures import Headers


def _client_id(n: int) -> str:
    return str(uuid.UUID(int=n))


def _jpeg_bytes(size: int = 224) -> bytes:
    buf = BytesIO()
    Image.new("RGB", (size, size), (120, 90, 60)).save(buf, format="JPEG")
    return buf.getvalue()


def _upload(data: bytes, content_type: str = "image/jpeg") -> UploadFile:
    return UploadFile(
        file=BytesIO(data),
        filename="leaf.jpg",
        headers=Headers({"content-type": content_type}),
    )


def _fixed_result() -> ScanResult:
    return ScanResult(
        disease_id=1,
        disease_name="Late Blight",
        crop_id=101,
        confidence=0.92,
        provider="baseline",
        model_name="rule-baseline",
        model_version="baseline-v1",
        inference_time_ms=1.5,
        dataset_version="v1",
        rankings=[
            PredictedDisease(
                disease_name="Powdery Mildew",
                confidence=0.7,
                disease_id=2,
                crop_id=101,
            )
        ],
    )


class _StubHeatmap:
    """Deterministic heatmap provider (Task 5.2) for pipeline tests."""

    provider_name = "baseline"

    def heatmap(self, _image, class_name=None):  # noqa: ARG002
        return HeatmapResult(heatmap=np.zeros((8, 8), dtype=np.float32), time_ms=3.5)


class _StubDetection:
    """Deterministic detector for pipeline tests.

    Switches: ``fail`` (predict raises), ``slow`` (predict sleeps past the
    timeout), ``heatmap_fail`` (explainer unavailable → heatmap raises).
    """

    def __init__(
        self, *, fail: bool = False, slow: bool = False, heatmap_fail: bool = False
    ) -> None:
        self._fail = fail
        self._slow = slow
        self.explainer = None if heatmap_fail else _StubHeatmap()

    async def predict_async(self, _image):  # noqa: ARG002
        if self._fail:
            raise InferenceError("model unavailable")
        if self._slow:
            await asyncio.sleep(1.0)
        return _fixed_result()

    def generate_heatmap(self, image, class_name):  # noqa: ARG002
        if self.explainer is None:
            raise InferenceError("no explainability provider is available")
        return self.explainer.heatmap(image, class_name)

    async def generate_heatmap_async(self, image, class_name):
        return self.generate_heatmap(image, class_name)


class _FailingStorage:
    """Storage adapter whose writes always fail (disk-full simulation)."""

    def save(self, _data, _content_type, _user_id, subdir=""):  # noqa: ARG002
        del subdir  # storage API parity; always fails in this stub
        raise OSError("disk full")

    def delete(self, _key):  # noqa: ARG002
        pass

    def url(self, _key):  # noqa: ARG002
        return ""


def _service(db, tmp_path, *, detection=None, **kw) -> ScanPipelineService:
    return ScanPipelineService(
        db,
        detection if detection is not None else _StubDetection(),
        LocalStorageService(tmp_path),
        OpenCVPreprocessor(),
        **kw,
    )


# ── Happy path ───────────────────────────────────────────────────────────


async def test_upload_persists_scan_and_images(db, tmp_path):
    svc = _service(db, tmp_path)
    scan, created = await svc.process_upload(
        user_id=1,
        files=[_upload(_jpeg_bytes())],
        client_scan_id=_client_id(1),
        part_type="leaf",
        device_id="dev-1",
    )
    assert created is True
    assert scan.disease_name == "Late Blight"
    assert scan.confidence == 0.92
    assert scan.provider == "baseline"
    assert scan.part_type == "leaf"
    assert scan.device_id == "dev-1"
    assert scan.dataset_version == "v1"
    assert scan.inference_time_ms == 1.5
    assert scan.processing_time_ms >= 0
    # Explainability prep persisted the model-input image alongside the source.
    assert scan.image_path
    assert scan.processed_image_path
    assert (tmp_path / scan.image_path).exists()
    assert (tmp_path / scan.processed_image_path).exists()
    # Task 5.2 — Grad-CAM heatmap generated + persisted during prediction.
    assert scan.heatmap_path
    assert (tmp_path / scan.heatmap_path).exists()
    meta = scan.ai_metadata
    assert meta["grad_cam"]["provider"] == "baseline"
    assert meta["grad_cam"]["time_ms"] == 3.5
    assert meta["grad_cam"]["overlay_path"] == scan.heatmap_path
    assert (tmp_path / meta["grad_cam"]["heatmap_path"]).exists()
    assert len(scan.media_items) == 1
    item = scan.media_items[0]
    assert item["source_type"] == "upload"
    assert item["part_type"] == "leaf"
    assert item["width"] == 224 and item["height"] == 224
    assert scan.rankings[0]["disease_name"] == "Powdery Mildew"


async def test_multiple_images_all_stored(db, tmp_path):
    svc = _service(db, tmp_path)
    scan, _ = await svc.process_upload(
        user_id=1,
        files=[_upload(_jpeg_bytes()), _upload(_jpeg_bytes())],
        client_scan_id=_client_id(11),
    )
    assert len(scan.media_items) == 2
    assert scan.media_items[0]["path"] != scan.media_items[1]["path"]


# ── Explainability (Task 5.2) ────────────────────────────────────────────


async def test_scan_stores_top5_confidence_and_model_metadata(db, tmp_path):
    svc = _service(db, tmp_path)
    scan, _ = await svc.process_upload(
        user_id=1, files=[_upload(_jpeg_bytes())], client_scan_id=_client_id(12)
    )
    meta = scan.ai_metadata
    assert meta["top5"][0] == {
        "disease_name": "Late Blight",
        "confidence": 0.92,
        "disease_id": 1,
        "crop_id": 101,
    }
    assert [c["disease_name"] for c in meta["top5"]] == ["Late Blight", "Powdery Mildew"]
    assert meta["confidence"] == {"top": 0.92, "level": "high"}
    assert meta["model"] == {
        "provider": "baseline",
        "model_name": "rule-baseline",
        "model_version": "baseline-v1",
        "dataset_version": "v1",
    }


async def test_heatmap_failure_degrades_gracefully(db, tmp_path):
    svc = _service(db, tmp_path, detection=_StubDetection(heatmap_fail=True))
    scan, created = await svc.process_upload(
        user_id=1, files=[_upload(_jpeg_bytes())], client_scan_id=_client_id(13)
    )
    assert created is True
    assert scan.disease_name == "Late Blight"  # diagnosis still stands
    assert scan.heatmap_path is None
    assert scan.ai_metadata["grad_cam"] is None


# ── Idempotency ──────────────────────────────────────────────────────────


async def test_replay_returns_existing_row(db, tmp_path):
    svc = _service(db, tmp_path)
    client_scan_id = _client_id(2)
    first, created_first = await svc.process_upload(
        user_id=1, files=[_upload(_jpeg_bytes())], client_scan_id=client_scan_id
    )
    second, created_second = await svc.process_upload(
        user_id=1, files=[_upload(_jpeg_bytes())], client_scan_id=client_scan_id
    )
    assert created_first is True
    assert created_second is False
    assert second.id == first.id


# ── Input rejection ──────────────────────────────────────────────────────


async def test_no_images_rejected(db, tmp_path):
    svc = _service(db, tmp_path)
    with pytest.raises(ImageRejectedError):
        await svc.process_upload(user_id=1, files=[], client_scan_id=_client_id(10))


async def test_too_many_images_rejected(db, tmp_path):
    svc = _service(db, tmp_path, max_images=2)
    with pytest.raises(ImageRejectedError):
        await svc.process_upload(
            user_id=1,
            files=[_upload(_jpeg_bytes()) for _ in range(3)],
            client_scan_id=_client_id(9),
        )


async def test_invalid_image_rejected(db, tmp_path):
    svc = _service(db, tmp_path)
    with pytest.raises(ImageRejectedError):
        await svc.process_upload(
            user_id=1,
            files=[_upload(b"not an image", "image/jpeg")],
            client_scan_id=_client_id(3),
        )


async def test_unsupported_content_type_rejected(db, tmp_path):
    svc = _service(db, tmp_path)
    with pytest.raises(UnsupportedFormatError):
        await svc.process_upload(
            user_id=1,
            files=[_upload(b"%PDF-1.4 some pdf", "application/pdf")],
            client_scan_id=_client_id(4),
        )


async def test_corrupted_image_rejected(db, tmp_path):
    svc = _service(db, tmp_path)
    garbage = b"\xff\xd8\xff" + b"\x00" * 256  # jpeg magic, undecodable body
    with pytest.raises(ImageRejectedError):
        await svc.process_upload(
            user_id=1,
            files=[_upload(garbage, "image/jpeg")],
            client_scan_id=_client_id(5),
        )


# ── Downstream failures ──────────────────────────────────────────────────


async def test_inference_failure_maps_to_502(db, tmp_path):
    svc = _service(db, tmp_path, detection=_StubDetection(fail=True))
    with pytest.raises(InferenceFailedError):
        await svc.process_upload(
            user_id=1, files=[_upload(_jpeg_bytes())], client_scan_id=_client_id(6)
        )


async def test_inference_timeout_maps_to_504(db, tmp_path):
    svc = _service(
        db,
        tmp_path,
        detection=_StubDetection(slow=True),
        timeout_seconds=0.05,
    )
    with pytest.raises(ScanTimeoutError):
        await svc.process_upload(
            user_id=1, files=[_upload(_jpeg_bytes())], client_scan_id=_client_id(7)
        )


async def test_storage_failure_maps_to_503(db, tmp_path):
    svc = ScanPipelineService(
        db,
        _StubDetection(),
        _FailingStorage(),
        OpenCVPreprocessor(),
    )
    with pytest.raises(StorageFailedError):
        await svc.process_upload(
            user_id=1, files=[_upload(_jpeg_bytes())], client_scan_id=_client_id(8)
        )


# ── Offline sync path (Task 6.2) ─────────────────────────────────────────
# process_sync_item feeds base64 images into the *same* _process_images core
# as process_upload, so the assertions below mirror the upload-path tests and
# verify the two origins are byte-for-byte equivalent downstream.


def _sync_item(
    data: bytes | None = None,
    *,
    client_id: str | None = None,
    content_type: str = "image/jpeg",
    images: list[bytes] | None = None,
    crop_id: int | None = None,
    part_type: str | None = None,
    device_id: str | None = None,
) -> ScanSyncItemIn:
    """Build a sync queue entry carrying base64-encoded JPEG(s)."""
    if images is None:
        images = [_jpeg_bytes()] if data is None else [data]
    return ScanSyncItemIn(
        client_scan_id=client_id or _client_id(20),
        images=[
            SyncImageIn(
                data=base64.b64encode(raw).decode("ascii"),
                content_type=content_type,
                filename="leaf.jpg",
            )
            for raw in images
        ],
        crop_id=crop_id,
        part_type=part_type,
        device_id=device_id,
    )


async def test_sync_item_persists_scan_and_images(db, tmp_path):
    svc = _service(db, tmp_path)
    scan, created = await svc.process_sync_item(
        user_id=1,
        item=_sync_item(client_id=_client_id(32), part_type="leaf", device_id="dev-sync"),
    )
    assert created is True
    assert scan.disease_name == "Late Blight"
    assert scan.confidence == 0.92
    assert scan.part_type == "leaf"
    assert scan.device_id == "dev-sync"
    # Sync rows are stamped as authoritative on the server.
    assert scan.synced_at is not None
    assert scan.image_path
    assert (tmp_path / scan.image_path).exists()
    # Explainability persisted alongside the source, same as uploads.
    assert scan.processed_image_path
    assert (tmp_path / scan.processed_image_path).exists()
    assert scan.heatmap_path
    assert (tmp_path / scan.heatmap_path).exists()
    meta = scan.ai_metadata
    assert meta["grad_cam"]["provider"] == "baseline"
    assert (tmp_path / meta["grad_cam"]["heatmap_path"]).exists()
    assert len(scan.media_items) == 1
    item = scan.media_items[0]
    assert item["source_type"] == "sync"
    assert item["part_type"] == "leaf"
    assert item["width"] == 224 and item["height"] == 224
    assert scan.rankings[0]["disease_name"] == "Powdery Mildew"


async def test_sync_item_multiple_images_all_stored(db, tmp_path):
    svc = _service(db, tmp_path)
    scan, _ = await svc.process_sync_item(
        user_id=1,
        item=_sync_item(client_id=_client_id(43), images=[_jpeg_bytes(), _jpeg_bytes()]),
    )
    assert len(scan.media_items) == 2
    assert all(item["source_type"] == "sync" for item in scan.media_items)
    assert scan.media_items[0]["path"] != scan.media_items[1]["path"]


async def test_sync_item_matches_upload_pipeline(db, tmp_path):
    """Online and offline origins produce identical prediction + explainability.

    The deterministic stub detector means every downstream stage — detection,
    Grad-CAM provenance, metadata persistence — must agree between the two
    entry points; only the media-item origin marker may differ.
    """
    svc = _service(db, tmp_path)
    jpeg = _jpeg_bytes()
    upload_scan, _ = await svc.process_upload(
        user_id=1, files=[_upload(jpeg)], client_scan_id=_client_id(30), part_type="leaf"
    )
    sync_scan, _ = await svc.process_sync_item(
        user_id=1, item=_sync_item(jpeg, client_id=_client_id(31), part_type="leaf")
    )

    # Identical prediction results.
    assert sync_scan.disease_name == upload_scan.disease_name == "Late Blight"
    assert sync_scan.confidence == upload_scan.confidence == 0.92
    assert sync_scan.provider == upload_scan.provider == "baseline"
    assert sync_scan.model_name == upload_scan.model_name
    assert sync_scan.model_version == upload_scan.model_version
    assert sync_scan.dataset_version == upload_scan.dataset_version

    # Identical Grad-CAM generation (provenance minus content-addressed keys).
    sync_meta, upload_meta = sync_scan.ai_metadata, upload_scan.ai_metadata
    for key in ("provider", "class_name", "time_ms"):
        assert sync_meta["grad_cam"][key] == upload_meta["grad_cam"][key]

    # Identical metadata persistence (top5, confidence band, model block).
    assert sync_meta["top5"] == upload_meta["top5"]
    assert sync_meta["confidence"] == upload_meta["confidence"]
    assert sync_meta["model"] == upload_meta["model"]

    # Identical storage artifacts (raw + overlay heatmaps, processed input).
    assert (tmp_path / sync_scan.heatmap_path).exists()
    assert (tmp_path / sync_scan.processed_image_path).exists()
    assert (tmp_path / sync_meta["grad_cam"]["heatmap_path"]).exists()

    # Origin is recorded distinctly, never conflated.
    assert sync_scan.media_items[0]["source_type"] == "sync"
    assert upload_scan.media_items[0]["source_type"] == "upload"
    assert sync_scan.synced_at is not None
    assert upload_scan.synced_at is None


async def test_sync_item_replay_returns_existing_row(db, tmp_path):
    svc = _service(db, tmp_path)
    client_scan_id = _client_id(33)
    first, created_first = await svc.process_sync_item(
        user_id=1, item=_sync_item(client_id=client_scan_id)
    )
    second, created_second = await svc.process_sync_item(
        user_id=1, item=_sync_item(client_id=client_scan_id)
    )
    assert created_first is True
    assert created_second is False
    assert second.id == first.id


async def test_sync_item_too_many_images_rejected(db, tmp_path):
    svc = _service(db, tmp_path, max_images=2)
    with pytest.raises(ImageRejectedError):
        await svc.process_sync_item(
            user_id=1,
            item=_sync_item(client_id=_client_id(35), images=[_jpeg_bytes() for _ in range(3)]),
        )


async def test_sync_item_invalid_base64_rejected(db, tmp_path):
    svc = _service(db, tmp_path)
    with pytest.raises(ImageRejectedError, match="base64"):
        await svc.process_sync_item(
            user_id=1,
            item=ScanSyncItemIn(
                client_scan_id=_client_id(36),
                images=[SyncImageIn(data="!!!not-base64!!!", content_type="image/jpeg")],
            ),
        )


async def test_sync_item_invalid_image_rejected(db, tmp_path):
    svc = _service(db, tmp_path)
    with pytest.raises(ImageRejectedError):
        await svc.process_sync_item(
            user_id=1, item=_sync_item(b"not an image", client_id=_client_id(37))
        )


async def test_sync_item_unsupported_content_type_rejected(db, tmp_path):
    svc = _service(db, tmp_path)
    with pytest.raises(UnsupportedFormatError):
        await svc.process_sync_item(
            user_id=1,
            item=_sync_item(
                b"%PDF-1.4 some pdf", content_type="application/pdf", client_id=_client_id(38)
            ),
        )


async def test_sync_item_inference_failure_maps_to_502(db, tmp_path):
    svc = _service(db, tmp_path, detection=_StubDetection(fail=True))
    with pytest.raises(InferenceFailedError):
        await svc.process_sync_item(user_id=1, item=_sync_item(client_id=_client_id(39)))


async def test_sync_item_inference_timeout_maps_to_504(db, tmp_path):
    svc = _service(db, tmp_path, detection=_StubDetection(slow=True), timeout_seconds=0.05)
    with pytest.raises(ScanTimeoutError):
        await svc.process_sync_item(user_id=1, item=_sync_item(client_id=_client_id(40)))


async def test_sync_item_storage_failure_maps_to_503(db, tmp_path):
    svc = ScanPipelineService(
        db,
        _StubDetection(),
        _FailingStorage(),
        OpenCVPreprocessor(),
    )
    with pytest.raises(StorageFailedError):
        await svc.process_sync_item(user_id=1, item=_sync_item(client_id=_client_id(41)))


async def test_sync_item_heatmap_failure_degrades_gracefully(db, tmp_path):
    svc = _service(db, tmp_path, detection=_StubDetection(heatmap_fail=True))
    scan, created = await svc.process_sync_item(
        user_id=1, item=_sync_item(client_id=_client_id(42))
    )
    assert created is True
    assert scan.disease_name == "Late Blight"  # diagnosis still stands
    assert scan.heatmap_path is None
    assert scan.ai_metadata["grad_cam"] is None
