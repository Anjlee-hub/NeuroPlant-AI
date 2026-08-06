"""M3, Task 4 tests — crop recovery tracker.

Covers the recovery policy (percentage from severity + logged treatments +
latest trend, status bands, risk from severity escalated by low confidence),
the nested ``/scans/{id}/recovery`` endpoints (ownership guard, log CRUD, 404s,
validation) and the self-contained tracker payload the Crop Doctor dashboard
renders. Content is whatever the farmer records — the policy is the only thing
asserted here.
"""

import uuid

from app.db.seed import seed_catalog
from app.db.session import async_session_factory
from app.models.recovery import RecoveryLog
from app.models.scan import Scan
from app.models.user import User
from app.schemas.scan import ScanCreate
from app.services.recovery import RecoveryTrackerService
from app.services.scans import ScanService
from sqlalchemy import select


def _uuid(n: int) -> str:
    return str(uuid.UUID(int=n))


async def _register(client, phone: str) -> dict:
    resp = await client.post(
        "/api/v1/auth/register",
        json={"phone": phone, "name": "Tester", "role": "farmer", "password": "secret123"},
    )
    assert resp.status_code == 201, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


async def _seed():
    async with async_session_factory() as db:
        await seed_catalog(db)


async def _make_scan(
    user_id: int,
    *,
    severity: str = "severe",
    confidence: float = 0.92,
    crop_id: int | None = None,
    disease_name: str = "Late Blight",
    variant: int = 0,
) -> int:
    """Persist a scan directly (bypasses inference) for deterministic tests.

    ``variant`` disambiguates the idempotency key when a test needs several
    scans for the same user.
    """
    async with async_session_factory() as db:
        scan = await ScanService(db).create(
            ScanCreate(
                client_scan_id=_uuid(8100 + user_id * 100 + variant),
                user_id=user_id,
                image_path="/media/test.jpg",
                media_items=[],
                crop_id=crop_id,
                part_type="leaf",
                disease_id=None,
                disease_name=disease_name,
                confidence=confidence,
                severity=severity,
                stage="early",
                provider="test",
                model_name="test-model",
                model_version="1.0",
                dataset_version="v1",
                preprocessing_time_ms=1.0,
                inference_time_ms=2.0,
                processing_time_ms=3.0,
                ai_metadata={},
                device_id="test-device",
                synced_at=None,
            )
        )
        return scan.id


async def _user_id(db, phone: str) -> int:
    user = await db.scalar(select(User).where(User.phone == phone))
    assert user is not None
    return user.id


async def _tomato_crop_id() -> int:
    from app.models.catalog import Crop

    async with async_session_factory() as db:
        crop = await db.scalar(select(Crop).where(Crop.name == "tomato"))
        assert crop is not None
        return crop.id


# ── Policy (pure, no DB) ──────────────────────────────────────────────────


def test_recovery_percentage_starts_from_severity():
    assert RecoveryTrackerService.recovery_percentage([], "severe") == 0.10
    assert RecoveryTrackerService.recovery_percentage([], "moderate") == 0.20
    assert RecoveryTrackerService.recovery_percentage([], "low") == 0.30
    assert RecoveryTrackerService.recovery_percentage([], None) == 0.20


def test_recovery_percentage_advances_per_log_and_trend():
    # moderate (0.20) + 2 logs (2 * 0.15) = 0.50.
    logs = [RecoveryLog(treatment_applied="a"), RecoveryLog(treatment_applied="b")]
    assert RecoveryTrackerService.recovery_percentage(logs, "moderate") == 0.50

    # Latest trend nudges it up (improving)…
    logs[-1].progress = "improving"
    assert RecoveryTrackerService.recovery_percentage(logs, "moderate") == 0.60

    # …or down (worsening).
    logs[-1].progress = "worsening"
    assert RecoveryTrackerService.recovery_percentage(logs, "moderate") == 0.40


def test_recovery_percentage_is_clamped():
    severe = RecoveryTrackerService.recovery_percentage([], "severe")
    # 0.10 + 8 * 0.15 = 1.30 → capped at 1.0.
    many = [RecoveryLog(treatment_applied=str(i)) for i in range(8)]
    assert RecoveryTrackerService.recovery_percentage(many, "severe") == 1.0
    # Worsening can't push below 0.
    bad = [RecoveryLog(treatment_applied="x", progress="worsening")]
    assert RecoveryTrackerService.recovery_percentage(bad, "severe") == 0.15
    assert severe >= 0.0


def test_recovery_status_thresholds():
    assert RecoveryTrackerService.status(1.0) == "recovered"
    assert RecoveryTrackerService.status(0.96) == "recovered"
    assert RecoveryTrackerService.status(0.70) == "improving"
    assert RecoveryTrackerService.status(0.60) == "improving"
    assert RecoveryTrackerService.status(0.40) == "on_track"
    assert RecoveryTrackerService.status(0.35) == "on_track"
    assert RecoveryTrackerService.status(0.10) == "at_risk"


def test_risk_from_severity_escalated_by_low_confidence():
    def scan(severity: str | None, confidence: float) -> Scan:
        return Scan(
            client_scan_id=_uuid(1),
            image_path="/media/x.jpg",
            disease_name="X",
            confidence=confidence,
            severity=severity,
        )

    assert RecoveryTrackerService.risk(scan("severe", 0.92)) == "high"
    assert RecoveryTrackerService.risk(scan("moderate", 0.92)) == "medium"
    assert RecoveryTrackerService.risk(scan("low", 0.92)) == "low"
    # Low detection confidence escalates the band one notch.
    assert RecoveryTrackerService.risk(scan("moderate", 0.4)) == "high"
    assert RecoveryTrackerService.risk(scan("low", 0.4)) == "medium"
    assert RecoveryTrackerService.risk(scan("severe", 0.4)) == "high"
    assert RecoveryTrackerService.risk(scan(None, 0.92)) == "medium"


# ── Endpoints ─────────────────────────────────────────────────────────────


async def test_recovery_endpoints_require_auth(client):
    assert (await client.get("/api/v1/scans/1/recovery")).status_code == 401
    assert (
        await client.post("/api/v1/scans/1/recovery/logs", json={"treatment_applied": "x"})
    ).status_code == 401
    assert (
        await client.patch(
            "/api/v1/scans/1/recovery/logs/1", json={"notes": "x"}
        )
    ).status_code == 401
    assert (await client.delete("/api/v1/scans/1/recovery/logs/1")).status_code == 401


async def test_tracker_happy_path(client, db):
    await _seed()
    headers = await _register(client, "+919100000001")
    user_id = await _user_id(db, "+919100000001")
    crop_id = await _tomato_crop_id()
    scan_id = await _make_scan(user_id, severity="severe", crop_id=crop_id)

    resp = await client.get(f"/api/v1/scans/{scan_id}/recovery", headers=headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()

    # Plant-overview summary, crop resolved to its display name.
    scan = body["scan"]
    assert scan["id"] == scan_id
    assert scan["disease_name"] == "Late Blight"
    assert scan["crop_name"] == "Tomato"
    assert scan["part_type"] == "leaf"
    assert scan["severity"] == "severe"
    assert scan["confidence"] == 0.92
    assert scan["model_version"] == "1.0"

    # Computed policy for a fresh severe diagnosis.
    assert body["risk"] == "high"
    assert body["recovery_percentage"] == 0.10
    assert body["status"] == "at_risk"
    assert body["total_treatments"] == 0
    assert body["timeline"] == []
    assert body["updated_at"] is None


async def test_add_log_updates_timeline_and_percentage(client, db):
    await _seed()
    headers = await _register(client, "+919100000002")
    user_id = await _user_id(db, "+919100000002")
    scan_id = await _make_scan(user_id, severity="moderate")

    resp = await client.post(
        f"/api/v1/scans/{scan_id}/recovery/logs",
        json={
            "treatment_applied": "Neem oil spray",
            "notes": "Sprayed both sides",
            "progress": "improving",
        },
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    log = resp.json()
    assert log["scan_id"] == scan_id
    assert log["treatment_applied"] == "Neem oil spray"
    assert log["progress"] == "improving"
    assert log["applied_at"]  # defaulted to now

    tracker = await client.get(f"/api/v1/scans/{scan_id}/recovery", headers=headers)
    body = tracker.json()
    # 0.20 + 0.15 (one log) + 0.10 (improving) = 0.45 → on_track.
    assert body["recovery_percentage"] == 0.45
    assert body["status"] == "on_track"
    assert body["total_treatments"] == 1
    assert len(body["timeline"]) == 1
    assert body["timeline"][0]["id"] == log["id"]
    assert body["updated_at"] is not None


async def test_add_log_validation(client, db):
    await _seed()
    headers = await _register(client, "+919100000003")
    user_id = await _user_id(db, "+919100000003")
    scan_id = await _make_scan(user_id)

    # Empty treatment is rejected.
    resp = await client.post(
        f"/api/v1/scans/{scan_id}/recovery/logs", json={"treatment_applied": ""}, headers=headers
    )
    assert resp.status_code == 422

    # Unknown progress vocabulary is rejected.
    resp = await client.post(
        f"/api/v1/scans/{scan_id}/recovery/logs",
        json={"treatment_applied": "Spray", "progress": "unknown"},
        headers=headers,
    )
    assert resp.status_code == 422


async def test_update_log_partial(client, db):
    await _seed()
    headers = await _register(client, "+919100000004")
    user_id = await _user_id(db, "+919100000004")
    scan_id = await _make_scan(user_id, severity="moderate")

    log_id = (
        await client.post(
            f"/api/v1/scans/{scan_id}/recovery/logs",
            json={"treatment_applied": "Neem oil", "notes": "day 1", "progress": "no-change"},
            headers=headers,
        )
    ).json()["id"]

    # Patch only the trend — notes untouched.
    resp = await client.patch(
        f"/api/v1/scans/{scan_id}/recovery/logs/{log_id}",
        json={"progress": "improving"},
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    log = resp.json()
    assert log["progress"] == "improving"
    assert log["notes"] == "day 1"
    assert log["treatment_applied"] == "Neem oil"

    # Tracker reflects the new trend: 0.20 + 0.15 + 0.10 = 0.45.
    tracker = await client.get(f"/api/v1/scans/{scan_id}/recovery", headers=headers)
    assert tracker.json()["recovery_percentage"] == 0.45


async def test_delete_log(client, db):
    await _seed()
    headers = await _register(client, "+919100000005")
    user_id = await _user_id(db, "+919100000005")
    scan_id = await _make_scan(user_id, severity="moderate")

    log_id = (
        await client.post(
            f"/api/v1/scans/{scan_id}/recovery/logs",
            json={"treatment_applied": "Neem oil"},
            headers=headers,
        )
    ).json()["id"]

    resp = await client.delete(f"/api/v1/scans/{scan_id}/recovery/logs/{log_id}", headers=headers)
    assert resp.status_code == 204

    tracker = await client.get(f"/api/v1/scans/{scan_id}/recovery", headers=headers)
    body = tracker.json()
    assert body["total_treatments"] == 0
    assert body["timeline"] == []
    assert body["recovery_percentage"] == 0.20  # back to severity base


async def test_recovery_404_for_unknown_or_other_users_scan(client, db):
    await _seed()
    headers = await _register(client, "+919100000006")
    user_id = await _user_id(db, "+919100000006")
    scan_id = await _make_scan(user_id)

    # Unknown scan.
    assert (await client.get("/api/v1/scans/999999/recovery", headers=headers)).status_code == 404

    # Another user's scan is indistinguishable (enumeration guard).
    other = await _register(client, "+919100000007")
    assert (await client.get(f"/api/v1/scans/{scan_id}/recovery", headers=other)).status_code == 404
    assert (
        await client.post(
            f"/api/v1/scans/{scan_id}/recovery/logs",
            json={"treatment_applied": "x"},
            headers=other,
        )
    ).status_code == 404


async def test_recovery_log_404_when_not_on_this_scan(client, db):
    await _seed()
    headers = await _register(client, "+919100000008")
    user_id = await _user_id(db, "+919100000008")
    scan_a = await _make_scan(user_id)
    scan_b = await _make_scan(user_id, variant=1)

    log_id = (
        await client.post(
            f"/api/v1/scans/{scan_a}/recovery/logs",
            json={"treatment_applied": "Neem oil"},
            headers=headers,
        )
    ).json()["id"]

    # The log belongs to scan A — editing it via scan B is a 404.
    resp = await client.patch(
        f"/api/v1/scans/{scan_b}/recovery/logs/{log_id}",
        json={"progress": "improving"},
        headers=headers,
    )
    assert resp.status_code == 404
    assert "recovery log" in resp.json()["error"]["message"].lower()

    resp = await client.delete(f"/api/v1/scans/{scan_b}/recovery/logs/{log_id}", headers=headers)
    assert resp.status_code == 404


async def test_risk_reflected_in_tracker_payload(client, db):
    """A low-confidence low-severity scan reports medium risk, not low."""
    await _seed()
    headers = await _register(client, "+919100000009")
    user_id = await _user_id(db, "+919100000009")
    scan_id = await _make_scan(user_id, severity="low", confidence=0.4)

    resp = await client.get(f"/api/v1/scans/{scan_id}/recovery", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["risk"] == "medium"
