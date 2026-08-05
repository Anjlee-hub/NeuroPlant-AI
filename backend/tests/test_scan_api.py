"""API tests for POST /scans (M2, Task 4.2).

End-to-end over HTTP: multipart upload → validation → storage → detection →
persistence, plus the status-code contract (201 created / 200 idempotent
replay), authorization, rate limiting and downstream AI failure mapping.
"""

import uuid
from io import BytesIO

from app.ai.types import InferenceError
from app.core.rate_limit import RateLimiter
from app.db.seed import seed_catalog
from PIL import Image


def _jpeg_bytes() -> bytes:
    buf = BytesIO()
    Image.new("RGB", (224, 224), (120, 90, 60)).save(buf, format="JPEG")
    return buf.getvalue()


def _client_id(n: int) -> str:
    return str(uuid.UUID(int=n))


async def _auth_headers(client, phone: str) -> dict:
    resp = await client.post(
        "/api/v1/auth/register",
        json={"phone": phone, "name": "Tester", "role": "farmer", "password": "secret123"},
    )
    assert resp.status_code == 201, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def _files(images: tuple[bytes, ...]) -> list[tuple[str, tuple[str, bytes, str]]]:
    return [("files", ("leaf.jpg", data, "image/jpeg")) for data in images]


async def _upload(
    client,
    headers: dict,
    *,
    client_scan_id: str,
    images: tuple[bytes, ...] = (_jpeg_bytes(),),
    part_type: str | None = None,
):
    form: dict[str, str] = {"client_scan_id": client_scan_id}
    if part_type is not None:
        form["part_type"] = part_type
    return await client.post("/api/v1/scans", files=_files(images), data=form, headers=headers)


# ── Authorization ────────────────────────────────────────────────────────


async def test_upload_requires_auth(client):
    resp = await client.post(
        "/api/v1/scans",
        files=_files((_jpeg_bytes(),)),
        data={"client_scan_id": _client_id(1)},
    )
    assert resp.status_code == 401


# ── Happy path ───────────────────────────────────────────────────────────


async def test_upload_success(client, db):
    await seed_catalog(db)
    headers = await _auth_headers(client, "+919000000011")
    resp = await _upload(client, headers, client_scan_id=_client_id(2))
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["disease_name"]
    assert body["confidence"] == 0.6  # rule-baseline marker
    assert body["provider"] == "baseline"
    assert body["image_path"]
    assert body["processed_image_path"]
    assert body["heatmap_path"]  # Task 5.2 — Grad-CAM stored during upload
    assert body["sync_status"] == "synced"
    assert isinstance(body["rankings"], list)
    assert len(body["media_items"]) == 1
    assert body["media_items"][0]["source_type"] == "upload"


async def test_upload_multiple_images(client, db):
    await seed_catalog(db)
    headers = await _auth_headers(client, "+919000000017")
    resp = await _upload(
        client,
        headers,
        client_scan_id=_client_id(9),
        images=(_jpeg_bytes(), _jpeg_bytes()),
    )
    assert resp.status_code == 201, resp.text
    assert len(resp.json()["media_items"]) == 2


async def test_upload_accepts_part_type(client, db):
    await seed_catalog(db)
    headers = await _auth_headers(client, "+919000000019")
    resp = await _upload(client, headers, client_scan_id=_client_id(12), part_type="leaf")
    assert resp.status_code == 201, resp.text
    assert resp.json()["part_type"] == "leaf"


# ── Input rejection ──────────────────────────────────────────────────────


async def test_upload_invalid_image(client, db):
    await seed_catalog(db)
    headers = await _auth_headers(client, "+919000000012")
    resp = await client.post(
        "/api/v1/scans",
        files=[("files", ("leaf.jpg", b"not an image", "image/jpeg"))],
        data={"client_scan_id": _client_id(3)},
        headers=headers,
    )
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "invalid_image"


async def test_upload_unsupported_format(client, db):
    await seed_catalog(db)
    headers = await _auth_headers(client, "+919000000013")
    resp = await client.post(
        "/api/v1/scans",
        files=[("files", ("doc.pdf", b"%PDF-1.4 body", "application/pdf"))],
        data={"client_scan_id": _client_id(4)},
        headers=headers,
    )
    assert resp.status_code == 415
    assert resp.json()["error"]["code"] == "unsupported_format"


async def test_upload_corrupted_file(client, db):
    await seed_catalog(db)
    headers = await _auth_headers(client, "+919000000014")
    garbage = b"\xff\xd8\xff" + b"\x00" * 256  # jpeg magic, undecodable body
    resp = await client.post(
        "/api/v1/scans",
        files=[("files", ("leaf.jpg", garbage, "image/jpeg"))],
        data={"client_scan_id": _client_id(5)},
        headers=headers,
    )
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "invalid_image"


async def test_upload_too_many_images(client, db):
    await seed_catalog(db)
    headers = await _auth_headers(client, "+919000000018")
    resp = await _upload(
        client,
        headers,
        client_scan_id=_client_id(10),
        images=tuple(_jpeg_bytes() for _ in range(6)),
    )
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "invalid_image"


async def test_upload_invalid_client_scan_id(client, db):
    await seed_catalog(db)
    headers = await _auth_headers(client, "+919000000016")
    resp = await client.post(
        "/api/v1/scans",
        files=_files((_jpeg_bytes(),)),
        data={"client_scan_id": "not-a-uuid"},
        headers=headers,
    )
    assert resp.status_code == 422


async def test_upload_invalid_part_type(client, db):
    await seed_catalog(db)
    headers = await _auth_headers(client, "+919000000020")
    resp = await _upload(client, headers, client_scan_id=_client_id(13), part_type="nonsense")
    assert resp.status_code == 422


# ── Idempotency ──────────────────────────────────────────────────────────


async def test_duplicate_client_scan_id_returns_existing(client, db):
    await seed_catalog(db)
    headers = await _auth_headers(client, "+919000000015")
    client_scan_id = _client_id(6)
    first = await _upload(client, headers, client_scan_id=client_scan_id)
    assert first.status_code == 201, first.text
    second = await _upload(client, headers, client_scan_id=client_scan_id)
    assert second.status_code == 200
    assert second.json()["id"] == first.json()["id"]


# ── Downstream failures ──────────────────────────────────────────────────


async def test_ai_failure_returns_502(client, db):
    await seed_catalog(db)
    from app.main import app

    class _BrokenDetection:
        async def predict_async(self, _image):  # noqa: ARG002
            raise InferenceError("model unavailable")

    app.state.detection_service = _BrokenDetection()
    headers = await _auth_headers(client, "+919000000021")
    resp = await _upload(client, headers, client_scan_id=_client_id(7))
    assert resp.status_code == 502
    assert resp.json()["error"]["code"] == "inference_failed"


async def test_upload_rate_limited(client, db, monkeypatch):
    await seed_catalog(db)
    import app.api.v1.deps as deps_mod

    limiter = RateLimiter(capacity=1, refill_per_sec=0.0, enabled=True)
    monkeypatch.setattr(deps_mod, "get_scan_limiter", lambda: limiter)
    headers = await _auth_headers(client, "+919000000022")
    first = await _upload(client, headers, client_scan_id=_client_id(8))
    assert first.status_code == 201, first.text
    second = await _upload(client, headers, client_scan_id=_client_id(11))
    assert second.status_code == 429
