"""M3, Task 5 tests — smart crop calendar & reminder system.

Covers the crop-picker catalog (growth-stage templates), schedule creation
(stage ranges, task generation, default planting-window, idempotency,
regeneration), the Farmer Calendar dashboard (today / upcoming / overdue /
completed buckets + progress), task management (complete / snooze / notes /
custom tasks / delete), ownership guards (404 for other users' rows) and the
disease-aware overlay that adapts reminders to the crop's diagnoses and the
farmer's recovery logs.
"""

import uuid
from datetime import UTC, date, datetime, timedelta

from app.db.seed import (
    seed_catalog,
    seed_crop_calendar,
    seed_recommendations,
    seed_soil_recommendations,
)
from app.db.session import async_session_factory
from app.models.catalog import Crop, Disease
from app.models.user import User
from app.schemas.scan import ScanCreate
from app.services.scans import ScanService
from sqlalchemy import select


def _uuid(n: int) -> str:
    return str(uuid.UUID(int=n))


def _utc_today() -> date:
    return datetime.now(UTC).date()


async def _seed():
    """Full catalogs: crops/diseases + treatment + soil + calendar."""
    async with async_session_factory() as db:
        await seed_catalog(db)
        await seed_recommendations(db)
        await seed_soil_recommendations(db)
        await seed_crop_calendar(db)


async def _register(client, phone: str) -> dict:
    resp = await client.post(
        "/api/v1/auth/register",
        json={"phone": phone, "name": "Tester", "role": "farmer", "password": "secret123"},
    )
    assert resp.status_code == 201, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


async def _user_id(db, phone: str) -> int:
    user = await db.scalar(select(User).where(User.phone == phone))
    assert user is not None
    return user.id


async def _crop_id(name: str = "tomato") -> int:
    async with async_session_factory() as db:
        crop = await db.scalar(select(Crop).where(Crop.name == name))
        assert crop is not None
        return crop.id


async def _disease_id(crop_name: str, disease_name: str) -> int:
    async with async_session_factory() as db:
        row = await db.scalar(
            select(Disease).join(Crop).where(Crop.name == crop_name, Disease.name == disease_name)
        )
        assert row is not None
        return row.id


async def _make_scan(
    user_id: int,
    *,
    crop_id: int | None = None,
    disease_id: int | None = None,
    disease_name: str = "Early Blight",
    severity: str = "severe",
    confidence: float = 0.92,
    variant: int = 0,
) -> int:
    async with async_session_factory() as db:
        scan = await ScanService(db).create(
            ScanCreate(
                client_scan_id=_uuid(9100 + user_id * 100 + variant),
                user_id=user_id,
                image_path="/media/test.jpg",
                media_items=[],
                crop_id=crop_id,
                part_type="leaf",
                disease_id=disease_id,
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


async def _schedule(client, headers, crop_name: str = "tomato", payload: dict | None = None):
    crop_id = await _crop_id(crop_name)
    resp = await client.post(
        f"/api/v1/calendar/crops/{crop_id}/schedule",
        json=payload or {},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


# ── Crop-picker catalog ────────────────────────────────────────────────────


async def test_catalog_requires_auth(client):
    assert (await client.get("/api/v1/calendar/crops")).status_code == 401
    assert (await client.post("/api/v1/calendar/crops/1/schedule", json={})).status_code == 401


async def test_crop_catalog_has_consistent_templates(client):
    await _seed()
    headers = await _register(client, "+919300000001")

    resp = await client.get("/api/v1/calendar/crops", headers=headers)
    assert resp.status_code == 200
    crops = resp.json()
    assert len(crops) == 12  # one plan per catalog crop
    for crop in crops:
        # The five stage durations sum to the crop's days-to-maturity.
        total = (
            crop["germination_days"]
            + crop["vegetative_days"]
            + crop["flowering_days"]
            + crop["fruiting_days"]
            + crop["harvest_days"]
        )
        assert total == crop["growth_days"]
        # Planting window is a real month range (1–12, wrapping allowed).
        assert 1 <= crop["planting_start_month"] <= 12
        assert 1 <= crop["planting_end_month"] <= 12


# ── Schedule creation ──────────────────────────────────────────────────────


async def test_schedule_happy_path(client, db):
    await _seed()
    headers = await _register(client, "+919300000002")
    body = await _schedule(client, headers, "tomato")

    today = _utc_today()
    assert body["crop_name"] == "Tomato"
    # August is inside tomato's Mar–Nov window → default planting is today.
    assert body["planting_date"] == today.isoformat()

    # Six contiguous stages: planting + the five growth ranges.
    stages = body["stages"]
    assert [s["stage"] for s in stages] == [
        "planting",
        "germination",
        "vegetative",
        "flowering",
        "fruiting",
        "harvest",
    ]
    assert stages[0]["start_date"] == stages[0]["end_date"] == today.isoformat()
    # Sowing day is germination day 0, so the marker overlaps germination's
    # start; the five growth ranges are then contiguous with no gaps.
    assert stages[1]["start_date"] == today.isoformat()
    for prev, cur in zip(stages[1:], stages[2:], strict=False):
        assert date.fromisoformat(cur["start_date"]) == date.fromisoformat(
            prev["end_date"]
        ) + timedelta(days=1)
    # Tomato is a 75-day crop → harvest ends 74 days after sowing.
    assert date.fromisoformat(stages[-1]["end_date"]) == today + timedelta(days=74)

    # Every core task kind is generated, all pending.
    kinds = {t["kind"] for t in body["tasks"]}
    assert {
        "watering",
        "fertilizer",
        "organic_treatment",
        "soil_inspection",
        "disease_monitoring",
    } <= kinds
    assert all(t["completed_at"] is None for t in body["tasks"])
    assert body["completed"] == 0
    assert body["total"] == len(body["tasks"]) > 0
    assert body["progress"] == 0.0


async def test_schedule_defaults_to_next_window_start(client, monkeypatch):
    from app.services import calendar as calendar_service

    monkeypatch.setattr(calendar_service, "_now", lambda: datetime(2026, 8, 1))
    await _seed()
    headers = await _register(client, "+919300000003")
    # Wheat window is Oct–Dec; August is outside → planting on Oct 1.
    body = await _schedule(client, headers, "wheat")
    assert body["planting_date"] == "2026-10-01"


async def test_schedule_is_idempotent_and_regenerates(client):
    await _seed()
    headers = await _register(client, "+919300000004")
    first = await _schedule(client, headers, "tomato")

    # Second call without regenerate is a no-op (same schedule id).
    again = await _schedule(client, headers, "tomato")
    assert again["schedule_id"] == first["schedule_id"]
    assert len(again["tasks"]) == len(first["tasks"])

    # A farmer-typed custom task survives no-op re-scheduling…
    schedule_id = first["schedule_id"]
    custom = (
        await client.post(
            "/api/v1/calendar/tasks",
            json={"schedule_id": schedule_id, "title": "Buy neem oil", "due_at": None},
            headers=headers,
        )
    ).json()
    assert custom["kind"] == "custom"

    # …but regenerate rebuilds the task list from scratch (custom dropped).
    regen = await _schedule(client, headers, "tomato", {"regenerate": True})
    assert regen["schedule_id"] == schedule_id
    assert all(t["kind"] != "custom" for t in regen["tasks"])


async def test_schedule_404_for_crop_without_plan(client):
    await _seed()
    headers = await _register(client, "+919300000005")
    resp = await client.post("/api/v1/calendar/crops/999999/schedule", json={}, headers=headers)
    assert resp.status_code == 404
    assert "calendar plan" in resp.json()["error"]["message"].lower()


# ── Dashboard buckets ──────────────────────────────────────────────────────


async def test_dashboard_buckets_and_progress(client):
    await _seed()
    headers = await _register(client, "+919300000006")
    body = await _schedule(client, headers, "tomato")
    schedule_id = body["schedule_id"]

    resp = await client.get("/api/v1/calendar", headers=headers)
    assert resp.status_code == 200
    dash = resp.json()
    assert len(dash["schedules"]) == 1
    schedule = dash["schedules"][0]
    assert schedule["schedule_id"] == schedule_id
    assert schedule["progress"] == 0.0
    assert schedule["completed"] == 0

    # Day-0 tasks (watering, basal fertilizer, soil check) are due today.
    assert dash["today_count"] == 3
    assert dash["overdue_count"] == 0
    assert dash["completed_count"] == 0
    assert dash["upcoming_count"] == len(schedule["tasks"]) - 3

    # Complete one of today's tasks → it moves into the completed bucket.
    task = next(t for t in schedule["tasks"] if t["due_at"][:10] == body["planting_date"])
    resp = await client.patch(
        f"/api/v1/calendar/tasks/{task['id']}",
        json={"completed": True},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["completed_at"] is not None

    dash = (await client.get("/api/v1/calendar", headers=headers)).json()
    assert dash["today_count"] == 2
    assert dash["completed_count"] == 1
    assert dash["schedules"][0]["completed"] == 1
    assert dash["schedules"][0]["progress"] == round(1 / len(schedule["tasks"]), 3)


# ── Task management ────────────────────────────────────────────────────────


async def test_task_snooze_advances_due_and_count(client):
    await _seed()
    headers = await _register(client, "+919300000007")
    body = await _schedule(client, headers, "tomato")
    task = next(t for t in body["tasks"] if t["kind"] == "watering")
    original_due = datetime.fromisoformat(task["due_at"].replace("Z", "+00:00"))

    resp = await client.patch(
        f"/api/v1/calendar/tasks/{task['id']}",
        json={"snooze_days": 2},
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    updated = resp.json()
    new_due = datetime.fromisoformat(updated["due_at"].replace("Z", "+00:00"))
    assert (new_due - original_due).days == 2
    assert updated["snooze_count"] == 1


async def test_task_title_and_notes_edit(client):
    await _seed()
    headers = await _register(client, "+919300000008")
    body = await _schedule(client, headers, "tomato")
    task_id = body["tasks"][0]["id"]

    resp = await client.patch(
        f"/api/v1/calendar/tasks/{task_id}",
        json={"title": "Water with drip line", "notes": "early morning"},
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    updated = resp.json()
    assert updated["title"] == "Water with drip line"
    assert updated["notes"] == "early morning"


async def test_custom_task_lifecycle(client):
    await _seed()
    headers = await _register(client, "+919300000009")
    body = await _schedule(client, headers, "tomato")
    schedule_id = body["schedule_id"]

    resp = await client.post(
        "/api/v1/calendar/tasks",
        json={"schedule_id": schedule_id, "title": "Buy fertilizer"},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    task = resp.json()
    assert task["kind"] == "custom"
    assert task["title"] == "Buy fertilizer"
    assert task["due_at"]  # defaulted to now

    # Visible in the dashboard.
    dash = (await client.get("/api/v1/calendar", headers=headers)).json()
    titles = {t["title"] for t in dash["schedules"][0]["tasks"]}
    assert "Buy fertilizer" in titles

    # Delete removes it.
    resp = await client.delete(f"/api/v1/calendar/tasks/{task['id']}", headers=headers)
    assert resp.status_code == 204
    dash = (await client.get("/api/v1/calendar", headers=headers)).json()
    titles = {t["title"] for t in dash["schedules"][0]["tasks"]}
    assert "Buy fertilizer" not in titles


async def test_custom_task_validation(client):
    await _seed()
    headers = await _register(client, "+919300000010")
    # Empty title is rejected.
    resp = await client.post(
        "/api/v1/calendar/tasks",
        json={"schedule_id": 1, "title": ""},
        headers=headers,
    )
    assert resp.status_code == 422


# ── Ownership guards ───────────────────────────────────────────────────────


async def test_task_operations_404_for_other_users(client, db):
    await _seed()
    owner = await _register(client, "+919300000011")
    body = await _schedule(client, owner, "tomato")
    schedule_id = body["schedule_id"]
    task_id = body["tasks"][0]["id"]

    intruder = await _register(client, "+919300000012")

    # Custom task on someone else's schedule is a 404.
    resp = await client.post(
        "/api/v1/calendar/tasks",
        json={"schedule_id": schedule_id, "title": "Sneak in"},
        headers=intruder,
    )
    assert resp.status_code == 404

    # Editing / deleting someone else's task is a 404.
    assert (
        await client.patch(
            f"/api/v1/calendar/tasks/{task_id}", json={"completed": True}, headers=intruder
        )
    ).status_code == 404
    assert (
        await client.delete(f"/api/v1/calendar/tasks/{task_id}", headers=intruder)
    ).status_code == 404

    # Unknown task is a 404 for everyone.
    assert (
        await client.patch("/api/v1/calendar/tasks/999999", json={"completed": True}, headers=owner)
    ).status_code == 404
    assert (await client.delete("/api/v1/calendar/tasks/999999", headers=owner)).status_code == 404


async def test_schedule_requires_auth(client):
    assert (await client.post("/api/v1/calendar/crops/1/schedule", json={})).status_code == 401
    assert (await client.get("/api/v1/calendar")).status_code == 401
    assert (
        await client.post("/api/v1/calendar/tasks", json={"schedule_id": 1, "title": "x"})
    ).status_code == 401


# ── Disease-aware overlay ──────────────────────────────────────────────────


async def test_disease_overlay_replaces_generic_reminders(client, db):
    """A severe tomato diagnosis tightens monitoring + adds treatment tasks."""
    await _seed()
    headers = await _register(client, "+919300000013")
    user_id = await _user_id(db, "+919300000013")
    tomato_id = await _crop_id("tomato")
    disease_id = await _disease_id("tomato", "Early Blight")
    await _make_scan(
        user_id,
        crop_id=tomato_id,
        disease_id=disease_id,
        disease_name="Early Blight",
        severity="severe",
    )

    body = await _schedule(client, headers, "tomato")

    # Disease monitoring is specific and linked to the scan.
    monitors = [t for t in body["tasks"] if t["kind"] == "disease_monitoring"]
    assert monitors
    assert all(t["title"].startswith("Monitor for Early Blight") for t in monitors)
    assert all(t["scan_id"] for t in monitors)  # push seam: linked to its scan

    # Generic protection reminders are replaced by disease-specific ones.
    titles = {t["title"] for t in body["tasks"]}
    assert "Apply organic crop protection" not in titles
    assert "Monitor the crop for pests and disease" not in titles
    assert any(t["kind"] == "organic_treatment" for t in body["tasks"])
    assert any(t["kind"] == "chemical_treatment" for t in body["tasks"])  # high risk


async def test_disease_overlay_honors_recovery_history(client, db):
    """The first disease reminder resumes after the latest recovery log."""
    await _seed()
    headers = await _register(client, "+919300000014")
    user_id = await _user_id(db, "+919300000014")
    tomato_id = await _crop_id("tomato")
    disease_id = await _disease_id("tomato", "Early Blight")
    scan_id = await _make_scan(
        user_id,
        crop_id=tomato_id,
        disease_id=disease_id,
        disease_name="Early Blight",
        severity="severe",
    )

    # Fresh diagnosis → monitoring starts today.
    body = await _schedule(client, headers, "tomato")
    today = _utc_today()
    first_monitor = min(
        t["due_at"][:10] for t in body["tasks"] if t["kind"] == "disease_monitoring"
    )
    assert first_monitor == today.isoformat()

    # Log an "improving" treatment today → the next reminder resumes in 7 days.
    resp = await client.post(
        f"/api/v1/scans/{scan_id}/recovery/logs",
        json={"treatment_applied": "Neem oil spray", "progress": "improving"},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text

    regen = await _schedule(client, headers, "tomato", {"regenerate": True})
    first_monitor = min(
        t["due_at"][:10] for t in regen["tasks"] if t["kind"] == "disease_monitoring"
    )
    assert first_monitor == (today + timedelta(days=7)).isoformat()
