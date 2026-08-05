"""API tests for POST /scans/sync (M2, Task 6.3).

End-to-end over HTTP: JSON batch sync → per-item independent processing →
idempotent replay → per-item failures → auth / ownership / rate-limit /
payload-size guards.
"""

import base64
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


def _b64(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")


def _item(client_scan_id: str, *, part_type: str | None = None) -> dict:
    """One valid sync item (a base64 JPEG)."""
    item: dict = {
        "client_scan_id": client_scan_id,
        "images": [
            {"data": _b64(_jpeg_bytes()), "content_type": "image/jpeg", "filename": "leaf.jpg"}
        ],
    }
    if part_type is not None:
        item["part_type"] = part_type
    return item


async def _auth_headers(client, phone: str) -> dict:
    resp = await client.post(
        "/api/v1/auth/register",
        json={"phone": phone, "name": "Tester", "role": "farmer", "password": "secret123"},
    )
    assert resp.status_code == 201, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


# ── Authorization ────────────────────────────────────────────────────────


async def test_sync_requires_auth(client):
    resp = await client.post("/api/v1/scans/sync", json=[_item(_client_id(1))])
    assert resp.status_code == 401


# ── Happy path ───────────────────────────────────────────────────────────


async def test_sync_success_batch(client, db):
    await seed_catalog(db)
    headers = await _auth_headers(client, "+919000000101")
    resp = await client.post(
        "/api/v1/scans/sync",
        json=[_item(_client_id(2), part_type="leaf"), _item(_client_id(3))],
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["total"] == 2
    assert body["created"] == 2
    assert body["replayed"] == 0
    assert body["failed"] == 0
    assert len(body["results"]) == 2
    for result in body["results"]:
        assert result["status"] == "created"
        assert result["error"] is None
        scan = result["scan"]
        assert scan["id"]
        assert scan["disease_name"]
        assert scan["confidence"] == 0.6  # rule-baseline marker
        assert scan["provider"] == "baseline"
        assert scan["model_version"]
        assert scan["sync_status"] == "synced"
        assert scan["synced_at"] is not None  # stamped by the sync path
        assert scan["media_items"][0]["source_type"] == "sync"
    assert body["results"][0]["scan"]["part_type"] == "leaf"


# ── Idempotency & replay ─────────────────────────────────────────────────


async def test_sync_duplicate_client_scan_id_replays(client, db):
    await seed_catalog(db)
    headers = await _auth_headers(client, "+919000000103")
    client_scan_id = _client_id(6)
    first = await client.post("/api/v1/scans/sync", json=[_item(client_scan_id)], headers=headers)
    assert first.status_code == 200, first.text
    assert first.json()["created"] == 1
    scan_id = first.json()["results"][0]["scan"]["id"]

    second = await client.post("/api/v1/scans/sync", json=[_item(client_scan_id)], headers=headers)
    assert second.status_code == 200, second.text
    body = second.json()
    assert body["created"] == 0
    assert body["replayed"] == 1
    result = body["results"][0]
    assert result["status"] == "replayed"
    assert result["error"] is None
    assert result["scan"]["id"] == scan_id  # existing authoritative row


async def test_sync_duplicate_within_batch(client, db):
    await seed_catalog(db)
    headers = await _auth_headers(client, "+919000000104")
    client_scan_id = _client_id(7)
    resp = await client.post(
        "/api/v1/scans/sync",
        json=[_item(client_scan_id), _item(client_scan_id)],
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["created"] == 1
    assert body["replayed"] == 1
    assert [r["status"] for r in body["results"]] == ["created", "replayed"]
    assert body["results"][0]["scan"]["id"] == body["results"][1]["scan"]["id"]


# ── Per-item isolation ───────────────────────────────────────────────────


async def test_sync_partial_failure_continues(client, db):
    await seed_catalog(db)
    headers = await _auth_headers(client, "+919000000102")
    good = _item(_client_id(4))
    bad = {
        "client_scan_id": _client_id(5),
        "images": [{"data": "!!!not-base64!!!", "content_type": "image/jpeg"}],
    }
    resp = await client.post("/api/v1/scans/sync", json=[good, bad], headers=headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["total"] == 2
    assert body["created"] == 1
    assert body["failed"] == 1
    by_id = {r["client_scan_id"]: r for r in body["results"]}
    assert by_id[good["client_scan_id"]]["status"] == "created"
    assert by_id[good["client_scan_id"]]["scan"]["id"]
    assert by_id[bad["client_scan_id"]]["status"] == "failed"
    assert by_id[bad["client_scan_id"]]["scan"] is None
    assert by_id[bad["client_scan_id"]]["error"]["code"] == "invalid_image"


async def test_sync_mixed_batch_statuses(client, db):
    await seed_catalog(db)
    headers = await _auth_headers(client, "+919000000111")
    replay_id = _client_id(13)
    await client.post("/api/v1/scans/sync", json=[_item(replay_id)], headers=headers)
    good_id = _client_id(14)
    bad_id = _client_id(15)
    payload = [
        _item(replay_id),  # already synced → replayed
        _item(good_id),  # new → created
        {
            "client_scan_id": bad_id,
            "images": [{"data": "!bad!", "content_type": "image/jpeg"}],
        },  # malformed → failed
    ]
    resp = await client.post("/api/v1/scans/sync", json=payload, headers=headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["total"] == 3
    assert body["created"] == 1
    assert body["replayed"] == 1
    assert body["failed"] == 1
    assert {r["status"] for r in body["results"]} == {"created", "replayed", "failed"}


# ── Ownership ────────────────────────────────────────────────────────────


async def test_sync_cross_user_duplicate_rejected(client, db):
    """Ownership guard: B can never reuse or see A's ``client_scan_id``.

    Idempotency replay is scoped to the owner, so B never receives A's row; the
    global unique constraint on ``client_scan_id`` turns B's attempt into a
    per-item ``duplicate_client_scan_id`` failure instead.
    """
    await seed_catalog(db)
    headers_a = await _auth_headers(client, "+919000000105")
    headers_b = await _auth_headers(client, "+919000000106")
    client_scan_id = _client_id(8)
    resp_a = await client.post(
        "/api/v1/scans/sync", json=[_item(client_scan_id)], headers=headers_a
    )
    assert resp_a.status_code == 200, resp_a.text
    assert resp_a.json()["created"] == 1

    resp_b = await client.post(
        "/api/v1/scans/sync", json=[_item(client_scan_id)], headers=headers_b
    )
    assert resp_b.status_code == 200, resp_b.text
    body = resp_b.json()
    assert body["created"] == 0
    assert body["replayed"] == 0  # never an implicit replay of A's scan
    assert body["failed"] == 1
    result = body["results"][0]
    assert result["status"] == "failed"
    assert result["scan"] is None
    assert result["error"]["code"] == "duplicate_client_scan_id"


# ── Downstream failures ──────────────────────────────────────────────────


async def test_sync_inference_failure_reports_failed(client, db):
    await seed_catalog(db)
    from app.main import app

    class _BrokenDetection:
        async def predict_async(self, _image):  # noqa: ARG002
            raise InferenceError("model unavailable")

    app.state.detection_service = _BrokenDetection()
    headers = await _auth_headers(client, "+919000000112")
    resp = await client.post("/api/v1/scans/sync", json=[_item(_client_id(16))], headers=headers)
    assert resp.status_code == 200, resp.text  # batch-level 200, per-item failure
    body = resp.json()
    assert body["failed"] == 1
    result = body["results"][0]
    assert result["status"] == "failed"
    assert result["scan"] is None
    assert result["error"]["code"] == "inference_failed"


# ── Rate limiting ────────────────────────────────────────────────────────


async def test_sync_rate_limited(client, db, monkeypatch):
    await seed_catalog(db)
    import app.api.v1.deps as deps_mod

    limiter = RateLimiter(capacity=1, refill_per_sec=0.0, enabled=True)
    monkeypatch.setattr(deps_mod, "get_scan_sync_limiter", lambda: limiter)
    headers = await _auth_headers(client, "+919000000107")
    first = await client.post("/api/v1/scans/sync", json=[_item(_client_id(9))], headers=headers)
    assert first.status_code == 200, first.text
    second = await client.post("/api/v1/scans/sync", json=[_item(_client_id(10))], headers=headers)
    assert second.status_code == 429


# ── Payload validation ───────────────────────────────────────────────────


async def test_sync_empty_batch_rejected(client, db):
    await seed_catalog(db)
    headers = await _auth_headers(client, "+919000000108")
    resp = await client.post("/api/v1/scans/sync", json=[], headers=headers)
    assert resp.status_code == 422
    assert resp.json()["detail"]["code"] == "empty_batch"


async def test_sync_batch_too_large_rejected(client, db):
    await seed_catalog(db)
    headers = await _auth_headers(client, "+919000000109")
    payload = [_item(_client_id(100 + i)) for i in range(51)]  # > scan_sync_max_items=50
    resp = await client.post("/api/v1/scans/sync", json=payload, headers=headers)
    assert resp.status_code == 413
    assert resp.json()["detail"]["code"] == "batch_too_large"


async def test_sync_malformed_item_rejected(client, db):
    await seed_catalog(db)
    headers = await _auth_headers(client, "+919000000110")
    bad_payloads = (
        [{"client_scan_id": "not-a-uuid", "images": [{"data": "x", "content_type": "image/jpeg"}]}],
        [{"client_scan_id": _client_id(11), "images": []}],
        [{"client_scan_id": _client_id(12), "images": [{"data": "x"}]}],  # missing content_type
        [
            {
                "client_scan_id": _client_id(13),
                "images": [{"data": "x", "content_type": "image/jpeg"}],
                "part_type": "nonsense",
            }
        ],
    )
    for payload in bad_payloads:
        resp = await client.post("/api/v1/scans/sync", json=payload, headers=headers)
        assert resp.status_code == 422, payload


# ── Full offline workflow (Task 6.4) ─────────────────────────────────────


async def test_sync_offline_queue_drain_and_retry(client, db):
    """Client drains its offline queue: partial failure → repair → replay.

    Mirrors the PWA IndexedDB drain: a first batch partially fails, the broken
    item is repaired and retried under the same ``client_scan_id`` (created),
    and re-syncing the whole queue replays every item with its existing
    authoritative row (no re-inference).
    """
    await seed_catalog(db)
    headers = await _auth_headers(client, "+919000000120")
    ok_1, ok_2, bad_id = _client_id(21), _client_id(22), _client_id(23)
    bad = {"client_scan_id": bad_id, "images": [{"data": "!broken!", "content_type": "image/jpeg"}]}

    # First drain: two items land, one fails without blocking the batch.
    first = await client.post(
        "/api/v1/scans/sync", json=[_item(ok_1), _item(ok_2), bad], headers=headers
    )
    assert first.status_code == 200, first.text
    body = first.json()
    assert body["created"] == 2
    assert body["failed"] == 1
    created_ids = {
        r["client_scan_id"]: r["scan"]["id"] for r in body["results"] if r["status"] == "created"
    }

    # Repair the failed item and retry under the same id — now it lands.
    retried = await client.post("/api/v1/scans/sync", json=[_item(bad_id)], headers=headers)
    retry_body = retried.json()
    assert retry_body["created"] == 1
    assert retry_body["results"][0]["status"] == "created"
    retry_id = retry_body["results"][0]["scan"]["id"]

    # Full re-sync of the queue: every item replays to its existing row.
    drain = await client.post(
        "/api/v1/scans/sync",
        json=[_item(ok_1), _item(ok_2), _item(bad_id)],
        headers=headers,
    )
    drain_body = drain.json()
    assert drain_body["created"] == 0
    assert drain_body["replayed"] == 3
    assert drain_body["failed"] == 0
    replay_ids = {r["scan"]["id"] for r in drain_body["results"]}
    assert replay_ids == {created_ids[ok_1], created_ids[ok_2], retry_id}
