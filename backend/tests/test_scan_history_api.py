"""API tests for the scan history endpoints (M2, Task 4.3).

Covers GET /scans (pagination / sorting / searching / filtering), GET
/scans/{id}, and DELETE /scans/{id} — including ownership isolation, admin
access, soft delete, the enumeration-guard 404s, and authorization errors.
"""

import uuid
from datetime import UTC, datetime, timedelta

from app.models.user import User
from app.schemas.scan import ScanCreate
from app.services.scans import ScanService
from sqlalchemy import select


def _client_id(n: int) -> str:
    return str(uuid.UUID(int=n))


def _payload(user_id: int, client_scan_id: str, **overrides) -> ScanCreate:
    values = dict(
        client_scan_id=client_scan_id,
        user_id=user_id,
        image_path=f"{user_id}/scan.jpg",
        media_items=[{"source_type": "upload", "path": f"{user_id}/scan.jpg", "part_type": "leaf"}],
        crop_id=101,
        part_type="leaf",
        disease_id=1,
        disease_name="Late Blight",
        confidence=0.9,
        severity="moderate",
        stage="early",
        provider="baseline",
        model_name="rule-baseline",
        model_version="baseline-v1",
        dataset_version="v1",
        preprocessing_time_ms=12.0,
        inference_time_ms=8.0,
        processing_time_ms=25.0,
        ai_metadata={
            "rankings": [{"disease_name": "Powdery Mildew", "confidence": 0.7, "disease_id": 2}]
        },
        device_id="dev-1",
    )
    values.update(overrides)
    return ScanCreate(**values)


async def _auth(client, db, phone: str, role: str = "farmer") -> tuple[User, dict]:
    resp = await client.post(
        "/api/v1/auth/register",
        json={"phone": phone, "name": "Tester", "role": role, "password": "secret123"},
    )
    assert resp.status_code == 201, resp.text
    user = await db.scalar(select(User).where(User.phone == phone))
    assert user is not None
    return user, {"Authorization": f"Bearer {resp.json()['access_token']}"}


async def _create(db, user_id: int, n: int, **overrides):
    """Create one scan; overrides apply to the ScanCreate payload."""
    return await ScanService(db).create(_payload(user_id, _client_id(300 + n), **overrides))


async def _backdate(db, scan, days: int) -> None:
    scan.created_at = (datetime.now(UTC) - timedelta(days=days)).replace(tzinfo=None)
    await db.commit()


# ── Authorization & empty history ───────────────────────────────────────


async def test_list_requires_auth(client):
    resp = await client.get("/api/v1/scans")
    assert resp.status_code == 401


async def test_list_empty_history(client, db):
    _, headers = await _auth(client, db, "+919000000101")
    resp = await client.get("/api/v1/scans", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["items"] == []
    assert body["total"] == 0
    assert body["page"] == 1
    assert body["has_next"] is False


# ── Pagination ──────────────────────────────────────────────────────────


async def test_list_paginates_with_has_next(client, db):
    user, headers = await _auth(client, db, "+919000000102")
    for i in range(5):
        await _create(db, user.id, i)

    page1 = await client.get("/api/v1/scans", headers=headers, params={"page": 1, "page_size": 2})
    page3 = await client.get("/api/v1/scans", headers=headers, params={"page": 3, "page_size": 2})
    assert page1.status_code == 200
    assert len(page1.json()["items"]) == 2
    assert page1.json()["total"] == 5
    assert page1.json()["has_next"] is True
    assert len(page3.json()["items"]) == 1
    assert page3.json()["has_next"] is False


async def test_list_rejects_invalid_pagination(client, db):
    _, headers = await _auth(client, db, "+919000000103")
    for params in ({"page": 0}, {"page_size": 0}, {"page_size": 101}):
        resp = await client.get("/api/v1/scans", headers=headers, params=params)
        assert resp.status_code == 422, params


# ── Searching / sorting / filtering ─────────────────────────────────────


async def test_list_searches_disease_or_provider(client, db):
    user, headers = await _auth(client, db, "+919000000104")
    await _create(db, user.id, 0, disease_name="Leaf Rust")
    await _create(db, user.id, 1, disease_name="Late Blight")
    await _create(db, user.id, 2, disease_name="Leaf Rust", provider="cloud-v1")

    resp = await client.get("/api/v1/scans", headers=headers, params={"search": "rust"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 2
    assert {item["disease_name"] for item in body["items"]} == {"Leaf Rust"}


async def test_list_sorts_newest_first_by_default(client, db):
    user, headers = await _auth(client, db, "+919000000105")
    scans = [await _create(db, user.id, i) for i in range(3)]
    for i, scan in enumerate(scans):
        await _backdate(db, scan, i)  # scan0 = 0d (newest) … scan2 = 2d (oldest)

    resp = await client.get("/api/v1/scans", headers=headers)
    ids = [item["id"] for item in resp.json()["items"]]
    assert ids == [scans[0].id, scans[1].id, scans[2].id]  # newest first


async def test_list_sorts_by_confidence_ascending(client, db):
    user, headers = await _auth(client, db, "+919000000106")
    await _create(db, user.id, 0, confidence=0.5)
    await _create(db, user.id, 1, confidence=0.9)
    await _create(db, user.id, 2, confidence=0.7)

    resp = await client.get(
        "/api/v1/scans", headers=headers, params={"sort": "confidence", "order": "asc"}
    )
    confs = [item["confidence"] for item in resp.json()["items"]]
    assert confs == [0.5, 0.7, 0.9]


async def test_list_filters_by_crop(client, db):
    user, headers = await _auth(client, db, "+919000000107")
    await _create(db, user.id, 0, crop_id=101)
    await _create(db, user.id, 1, crop_id=102)
    await _create(db, user.id, 2, crop_id=102)

    resp = await client.get("/api/v1/scans", headers=headers, params={"crop_id": 102})
    assert resp.json()["total"] == 2
    assert {item["crop_id"] for item in resp.json()["items"]} == {102}


async def test_list_filters_by_disease(client, db):
    user, headers = await _auth(client, db, "+919000000108")
    await _create(db, user.id, 0, disease_name="Leaf Rust")
    await _create(db, user.id, 1, disease_name="Powdery Mildew")

    resp = await client.get("/api/v1/scans", headers=headers, params={"disease": "mildew"})
    assert resp.json()["total"] == 1
    assert resp.json()["items"][0]["disease_name"] == "Powdery Mildew"


async def test_list_filters_by_part_type(client, db):
    user, headers = await _auth(client, db, "+919000000109")
    await _create(db, user.id, 0, part_type="leaf")
    await _create(db, user.id, 1, part_type="fruit")

    resp = await client.get("/api/v1/scans", headers=headers, params={"part_type": "fruit"})
    assert resp.json()["total"] == 1
    assert resp.json()["items"][0]["part_type"] == "fruit"


async def test_list_filters_by_date_range(client, db):
    user, headers = await _auth(client, db, "+919000000110")
    scans = [await _create(db, user.id, i) for i in range(3)]
    await _backdate(db, scans[0], 0)
    await _backdate(db, scans[1], 1)
    await _backdate(db, scans[2], 3)

    cutoff = datetime.now(UTC) - timedelta(days=2)
    resp = await client.get(
        "/api/v1/scans",
        headers=headers,
        params={"date_from": cutoff.isoformat()},
    )
    assert resp.json()["total"] == 2  # 0 and 1 days old


async def test_list_filters_by_confidence_range(client, db):
    user, headers = await _auth(client, db, "+919000000111")
    await _create(db, user.id, 0, confidence=0.5)
    await _create(db, user.id, 1, confidence=0.9)
    await _create(db, user.id, 2, confidence=0.7)

    resp = await client.get(
        "/api/v1/scans",
        headers=headers,
        params={"confidence_min": 0.6, "confidence_max": 0.8},
    )
    body = resp.json()
    assert body["total"] == 1
    assert body["items"][0]["confidence"] == 0.7


async def test_list_rejects_inverted_confidence_range(client, db):
    _, headers = await _auth(client, db, "+919000000112")
    resp = await client.get(
        "/api/v1/scans",
        headers=headers,
        params={"confidence_min": 0.9, "confidence_max": 0.1},
    )
    assert resp.status_code == 422


async def test_list_filters_by_severity(client, db):
    user, headers = await _auth(client, db, "+919000000113")
    await _create(db, user.id, 0, severity="low")
    await _create(db, user.id, 1, severity="severe")

    resp = await client.get("/api/v1/scans", headers=headers, params={"severity": "severe"})
    assert resp.json()["total"] == 1
    assert resp.json()["items"][0]["severity"] == "severe"


async def test_list_filters_by_sync_status(client, db):
    user, headers = await _auth(client, db, "+919000000114")
    await _create(db, user.id, 0)
    pending = await _create(db, user.id, 1)
    pending.sync_status = "pending"
    await db.commit()

    resp = await client.get("/api/v1/scans", headers=headers, params={"sync_status": "pending"})
    assert resp.json()["total"] == 1
    assert resp.json()["items"][0]["sync_status"] == "pending"


# ── Detail ──────────────────────────────────────────────────────────────


async def test_get_scan_detail_returns_full_record(client, db):
    user, headers = await _auth(client, db, "+919000000115")
    scan = await _create(db, user.id, 0)

    resp = await client.get(f"/api/v1/scans/{scan.id}", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] == scan.id
    assert body["disease_name"] == "Late Blight"
    assert body["confidence"] == 0.9
    assert body["severity"] == "moderate"
    assert body["stage"] == "early"
    assert body["model_version"] == "baseline-v1"
    assert body["dataset_version"] == "v1"
    assert body["provider"] == "baseline"
    assert body["preprocessing_time_ms"] == 12.0
    assert body["inference_time_ms"] == 8.0
    assert body["processing_time_ms"] == 25.0
    assert body["image_path"]
    assert body["media_items"][0]["source_type"] == "upload"
    assert body["rankings"][0]["disease_name"] == "Powdery Mildew"
    assert body["ai_metadata"]["rankings"][0]["disease_name"] == "Powdery Mildew"
    assert body["sync_status"] == "synced"


async def test_get_scan_other_users_scan_returns_404(client, db):
    owner, _ = await _auth(client, db, "+919000000116")
    scan = await _create(db, owner.id, 0)
    _, other_headers = await _auth(client, db, "+919000000117")

    resp = await client.get(f"/api/v1/scans/{scan.id}", headers=other_headers)
    assert resp.status_code == 404  # identical to "missing" — no enumeration


async def test_get_scan_missing_returns_404(client, db):
    _, headers = await _auth(client, db, "+919000000118")
    resp = await client.get("/api/v1/scans/999999", headers=headers)
    assert resp.status_code == 404


async def test_get_scan_invalid_id_returns_422(client, db):
    _, headers = await _auth(client, db, "+919000000119")
    resp = await client.get("/api/v1/scans/not-an-int", headers=headers)
    assert resp.status_code == 422


# ── Delete (soft) ───────────────────────────────────────────────────────


async def test_delete_returns_204_and_hides_scan(client, db):
    user, headers = await _auth(client, db, "+919000000120")
    scan = await _create(db, user.id, 0)

    resp = await client.delete(f"/api/v1/scans/{scan.id}", headers=headers)
    assert resp.status_code == 204

    gone = await client.get(f"/api/v1/scans/{scan.id}", headers=headers)
    assert gone.status_code == 404
    listing = await client.get("/api/v1/scans", headers=headers)
    assert listing.json()["total"] == 0


async def test_delete_other_users_scan_returns_404(client, db):
    owner, owner_headers = await _auth(client, db, "+919000000121")
    scan = await _create(db, owner.id, 0)
    _, other_headers = await _auth(client, db, "+919000000122")

    resp = await client.delete(f"/api/v1/scans/{scan.id}", headers=other_headers)
    assert resp.status_code == 404
    # And the scan is still intact for its owner.
    still = await client.get(f"/api/v1/scans/{scan.id}", headers=owner_headers)
    assert still.status_code == 200


async def test_delete_requires_auth(client):
    resp = await client.delete("/api/v1/scans/1")
    assert resp.status_code == 401


async def test_delete_invalid_id_returns_422(client, db):
    _, headers = await _auth(client, db, "+919000000123")
    resp = await client.delete("/api/v1/scans/abc", headers=headers)
    assert resp.status_code == 422


# ── Admin ───────────────────────────────────────────────────────────────


async def test_admin_lists_all_scans_and_filters_by_owner(client, db):
    owner, _ = await _auth(client, db, "+919000000124")
    scan_a = await _create(db, owner.id, 0)
    scan_b = await _create(db, owner.id, 1)
    _, admin_headers = await _auth(client, db, "+919000000125", role="admin")
    third, _ = await _auth(client, db, "+919000000126")
    await _create(db, third.id, 2)

    all_scans = await client.get("/api/v1/scans", headers=admin_headers)
    assert all_scans.json()["total"] == 3

    narrowed = await client.get(
        "/api/v1/scans", headers=admin_headers, params={"owner_id": owner.id}
    )
    assert narrowed.json()["total"] == 2
    assert {item["id"] for item in narrowed.json()["items"]} == {scan_a.id, scan_b.id}


async def test_admin_reads_any_scan(client, db):
    owner, _ = await _auth(client, db, "+919000000127")
    scan = await _create(db, owner.id, 0)
    _, admin_headers = await _auth(client, db, "+919000000128", role="admin")

    resp = await client.get(f"/api/v1/scans/{scan.id}", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()["id"] == scan.id


async def test_non_admin_cannot_narrow_by_owner_id(client, db):
    user, headers = await _auth(client, db, "+919000000129")
    my_scan = await _create(db, user.id, 0)
    other, _ = await _auth(client, db, "+919000000130")
    await _create(db, other.id, 1)

    # owner_id is ignored for non-admins: they still only see their own scans.
    resp = await client.get("/api/v1/scans", headers=headers, params={"owner_id": other.id})
    assert resp.json()["total"] == 1
    assert resp.json()["items"][0]["id"] == my_scan.id
