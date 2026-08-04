"""Service-level tests for the scan upload pipeline (M2, Task 4.2).

The pipeline is exercised with a stub detector (deterministic ScanResult) so
the tests cover validation → sanitize → storage → timing → persistence and the
error mapping without needing an AI artifact. API-level behaviour (auth, status
codes, idempotency over HTTP) is covered in test_scan_api.py.
"""

import asyncio
import uuid
from io import BytesIO

import pytest
from app.ai.opencv_preprocess import OpenCVPreprocessor
from app.ai.types import InferenceError, PredictedDisease
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


class _StubDetection:
    """Deterministic detector for pipeline tests (fail / slow switches)."""

    def __init__(self, *, fail: bool = False, slow: bool = False) -> None:
        self._fail = fail
        self._slow = slow

    async def predict_async(self, _image):  # noqa: ARG002
        if self._fail:
            raise InferenceError("model unavailable")
        if self._slow:
            await asyncio.sleep(1.0)
        return _fixed_result()


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
