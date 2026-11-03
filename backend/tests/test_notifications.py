"""M5, Task 2 tests — notifications foundation.

Covers authentication + strict ownership (enumeration guard: foreign/missing
ids → 404), service-level creation (type validation, empty-field guards,
scheduled_at seam), paginated listing with unread counts, mark-one / mark-all
read, and OpenAPI regression.
"""

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from app.db.session import async_session_factory
from app.main import app
from app.models.calendar import CalendarTask, CropSchedule
from app.models.catalog import Crop
from app.models.notification import Notification, NotificationType
from app.models.recovery import RecoveryLog
from app.models.scan import Scan
from app.services.notification_triggers import NotificationTriggerService
from app.services.notifications import (
    NotificationService,
    NotificationValidationError,
)
from sqlalchemy import func, select

# ── Helpers ────────────────────────────────────────────────────────────────


async def _register(client, phone: str) -> dict:
    resp = await client.post(
        "/api/v1/auth/register",
        json={"phone": phone, "name": "Tester", "role": "farmer", "password": "secret123"},
    )
    assert resp.status_code == 201, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


async def _register_and_get_id(client, phone: str) -> tuple[int, dict]:
    """Register a user and return their ID + auth headers from the response."""
    resp = await client.post(
        "/api/v1/auth/register",
        json={"phone": phone, "name": "Tester", "role": "farmer", "password": "secret123"},
    )
    assert resp.status_code == 201, resp.text
    access_token = resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}
    me_resp = await client.get("/api/v1/auth/me", headers=headers)
    assert me_resp.status_code == 200, me_resp.text
    return int(me_resp.json()["id"]), headers


async def _create_for(user_id: int, *, count: int = 1, **kwargs) -> list[Notification]:
    """Create notifications directly via the service (creation is not HTTP)."""
    created: list[Notification] = []
    async with async_session_factory() as db:
        service = NotificationService(db)
        for i in range(count):
            notif = await service.create(
                user_id,
                type=kwargs.get("type", NotificationType.WEATHER_RISK),
                title=kwargs.get("title", f"Weather alert {i}"),
                message=kwargs.get("message", f"Heavy rain expected — {i}"),
                payload=kwargs.get("payload", {"crop": "tomato"}),
                scheduled_at=kwargs.get("scheduled_at"),
            )
            created.append(notif)
    return created


# ── Authentication ─────────────────────────────────────────────────────────


async def test_notification_endpoints_require_auth(client):
    assert (await client.get("/api/v1/notifications")).status_code == 401
    assert (await client.get("/api/v1/notifications/unread-count")).status_code == 401
    assert (await client.patch("/api/v1/notifications/1/read")).status_code == 401
    assert (await client.patch("/api/v1/notifications/read-all")).status_code == 401


# ── Creation + type validation (service-level) ─────────────────────────────


async def test_create_accepts_enum_and_string_types():
    async with async_session_factory() as db:
        service = NotificationService(db)
        user_id = 1  # foreign key not enforced in unit test (no row needed)
        enum_notif = await service.create(
            user_id, type=NotificationType.DISEASE_RISK, title="Risk", message="High"
        )
        str_notif = await service.create(
            user_id, type="treatment_reminder", title="Reminder", message="Apply now"
        )
        assert enum_notif.type == NotificationType.DISEASE_RISK
        assert str_notif.type == NotificationType.TREATMENT_REMINDER
        assert str_notif.payload == {}


async def test_create_rejects_invalid_type():
    async with async_session_factory() as db:
        with pytest.raises(NotificationValidationError):
            await NotificationService(db).create(1, type="not_a_real_type", title="x", message="y")


async def test_create_rejects_blank_title_and_message():
    async with async_session_factory() as db:
        service = NotificationService(db)
        with pytest.raises(NotificationValidationError):
            await service.create(1, type="system", title="   ", message="y")
        with pytest.raises(NotificationValidationError):
            await service.create(1, type="system", title="x", message="")


async def test_create_sets_scheduled_at_without_sending():
    future = datetime.now(UTC) + timedelta(hours=1)
    async with async_session_factory() as db:
        notif = await NotificationService(db).create(
            1, type="task_reminder", title="Harvest", message="Tomorrow", scheduled_at=future
        )
        assert notif.scheduled_at == future
        assert notif.sent_at is None
        assert notif.read_at is None


# ── List / pagination / unread counts ──────────────────────────────────────


async def test_list_is_scoped_to_authenticated_user(client):
    """User A only sees their own notifications, never user B's."""
    user_a, headers_a = await _register_and_get_id(client, "+919000000401")
    user_b, _ = await _register_and_get_id(client, "+919000000402")
    await _create_for(user_a, count=3, title="A-alert")
    await _create_for(user_b, count=2, title="B-alert")
    resp = await client.get("/api/v1/notifications", headers=headers_a)
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 3
    assert body["unread"] == 3
    assert len(body["items"]) == 3
    assert all(item["title"].startswith("A-alert") for item in body["items"])
    assert not any(item["title"].startswith("B-alert") for item in body["items"])


async def test_list_pagination_and_limits(client):
    user_id, headers = await _register_and_get_id(client, "+919000000403")
    await _create_for(user_id, count=25)

    # Default page size (20) → page 1 has 20, total 25, pages 2.
    resp = await client.get("/api/v1/notifications", headers=headers)
    body = resp.json()
    assert len(body["items"]) == 20
    assert body["total"] == 25
    assert body["pages"] == 2
    assert body["page"] == 1

    # Page 2 → the remaining 5.
    resp = await client.get("/api/v1/notifications?page=2", headers=headers)
    body = resp.json()
    assert len(body["items"]) == 5
    assert body["page"] == 2

    # Sensible limit enforced at the boundary (100).
    resp = await client.get("/api/v1/notifications?page_size=500", headers=headers)
    assert resp.status_code == 422

    # Zero results is a valid (empty) page.
    resp = await client.get("/api/v1/notifications?page=99", headers=headers)
    body = resp.json()
    assert body["items"] == []
    assert body["total"] == 25
    assert body["pages"] == 2


async def test_list_newest_first(client):
    user_id, headers = await _register_and_get_id(client, "+919000000404")
    await _create_for(user_id, count=3, title="alert")
    resp = await client.get("/api/v1/notifications", headers=headers)
    items = resp.json()["items"]
    created = [item["created_at"] for item in items]
    assert created == sorted(created, reverse=True)  # newest first


# ── Unread count ───────────────────────────────────────────────────────────


async def test_unread_count_tracks_mark_read(client):
    user_id, headers = await _register_and_get_id(client, "+919000000405")
    notifs = await _create_for(user_id, count=3)

    resp = await client.get("/api/v1/notifications/unread-count", headers=headers)
    assert resp.json()["unread"] == 3

    # Mark one read → unread drops to 2.
    resp = await client.patch(f"/api/v1/notifications/{notifs[0].id}/read", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["updated"] == 1
    resp = await client.get("/api/v1/notifications/unread-count", headers=headers)
    assert resp.json()["unread"] == 2


async def test_unread_count_zero_for_fresh_user(client):
    _, headers = await _register_and_get_id(client, "+919000000406")
    resp = await client.get("/api/v1/notifications/unread-count", headers=headers)
    assert resp.json()["unread"] == 0


# ── Mark one read ──────────────────────────────────────────────────────────


async def test_mark_read_idempotent(client):
    user_id, headers = await _register_and_get_id(client, "+919000000407")
    notifs = await _create_for(user_id, count=1)

    resp = await client.patch(f"/api/v1/notifications/{notifs[0].id}/read", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["updated"] == 1
    # Second call still succeeds (already read) — no error, still "updated: 1".
    resp = await client.patch(f"/api/v1/notifications/{notifs[0].id}/read", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["updated"] == 1

    # And it's reflected in the list payload (read_at now set).
    resp = await client.get("/api/v1/notifications", headers=headers)
    item = resp.json()["items"][0]
    assert item["read_at"] is not None
    assert resp.json()["unread"] == 0


async def test_mark_read_foreign_notification_404(client):
    """Cross-user access is denied: user B cannot read user A's notification."""
    user_a, _ = await _register_and_get_id(client, "+919000000408")
    user_b, headers_b = await _register_and_get_id(client, "+919000000409")
    notifs = await _create_for(user_a, count=1)
    resp = await client.patch(f"/api/v1/notifications/{notifs[0].id}/read", headers=headers_b)
    assert resp.status_code == 404

    # The notification stays unread for user A.
    async with async_session_factory() as db:
        stored = await db.get(Notification, notifs[0].id)
        assert stored.read_at is None


async def test_mark_read_missing_id_404(client):
    _, headers = await _register_and_get_id(client, "+919000000410")
    resp = await client.patch("/api/v1/notifications/999999/read", headers=headers)
    assert resp.status_code == 404


# ── Mark all read ──────────────────────────────────────────────────────────


async def test_mark_all_read_returns_count(client):
    user_id, headers = await _register_and_get_id(client, "+919000000411")
    await _create_for(user_id, count=4)

    resp = await client.patch("/api/v1/notifications/read-all", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["updated"] == 4

    resp = await client.get("/api/v1/notifications/unread-count", headers=headers)
    assert resp.json()["unread"] == 0


async def test_mark_all_read_only_affects_own_notifications(client):
    user_a, headers_a = await _register_and_get_id(client, "+919000000412")
    user_b, headers_b = await _register_and_get_id(client, "+919000000413")
    await _create_for(user_a, count=2)
    await _create_for(user_b, count=3)

    resp = await client.patch("/api/v1/notifications/read-all", headers=headers_a)
    assert resp.json()["updated"] == 2

    # User B is untouched.
    resp = await client.get("/api/v1/notifications/unread-count", headers=headers_b)
    assert resp.json()["unread"] == 3


async def test_mark_all_read_idempotent(client):
    _, headers = await _register_and_get_id(client, "+919000000414")
    resp = await client.patch("/api/v1/notifications/read-all", headers=headers)
    assert resp.json()["updated"] == 0  # nothing to mark


# ── Scheduling seam ────────────────────────────────────────────────────────


class _RecordingTransport:
    """Test transport that records deliveries (proves the transport seam)."""

    def __init__(self) -> None:
        self.delivered: list[int] = []

    async def send(self, user, notification) -> None:
        self.delivered.append(notification.id)


async def test_scheduling_seam_dispatches_due_notifications():
    """dispatch_scheduled delivers due notifications and marks sent_at."""
    from app.db.session import async_session_factory
    from app.models.user import User
    from app.services.auth import register_user
    from sqlalchemy import select

    # Create a user for this test
    async with async_session_factory() as db:
        # Use the existing test user or create one
        user = await db.scalar(select(User).where(User.id == 1))
        if user is None:
            # Create user 1 if it doesn't exist
            user = await register_user(
                db, phone="+919999999991", name="Test", role="farmer", password="secret123"
            )

    user_id = user.id if user else 1
    past = datetime.now(UTC) - timedelta(minutes=5)
    future = datetime.now(UTC) + timedelta(hours=1)
    due = await _create_for(user_id, type="task_reminder", title="due", scheduled_at=past, count=1)
    not_due = await _create_for(
        user_id, type="task_reminder", title="later", scheduled_at=future, count=1
    )

    transport = _RecordingTransport()
    async with async_session_factory() as db:
        count = await NotificationService(db, transport=transport).dispatch_scheduled()

    assert count == 1
    assert transport.delivered == [due[0].id]
    assert not_due[0].id not in transport.delivered

    async with async_session_factory() as db:
        due_row = await db.get(Notification, due[0].id)
        not_due_row = await db.get(Notification, not_due[0].id)
        assert due_row.sent_at is not None
        assert not_due_row.sent_at is None


async def test_scheduling_seam_does_not_repeat_dispatch():
    """A sent notification is not dispatched again on the next tick."""
    from app.db.session import async_session_factory
    from app.models.user import User
    from app.services.auth import register_user
    from sqlalchemy import select

    async with async_session_factory() as db:
        user = await db.scalar(select(User).where(User.id == 1))
        if user is None:
            user = await register_user(
                db, phone="+919999999991", name="Test", role="farmer", password="secret123"
            )

    user_id = user.id if user else 1
    past = datetime.now(UTC) - timedelta(minutes=5)
    await _create_for(user_id, type="task_reminder", title="due", scheduled_at=past, count=1)

    transport = _RecordingTransport()
    async with async_session_factory() as db:
        first = await NotificationService(db, transport=transport).dispatch_scheduled()
        second = await NotificationService(db, transport=transport).dispatch_scheduled()

    assert first == 1
    assert second == 0
    assert len(transport.delivered) == 1


async def test_failed_scheduled_delivery_remains_retryable(client):
    user_id, _ = await _register_and_get_id(client, "+919000000425")
    due = datetime.now(UTC) - timedelta(minutes=5)

    class FailOnceTransport:
        def __init__(self) -> None:
            self.attempts = 0
            self.delivered: list[int] = []

        async def send(self, user, notification) -> None:
            self.attempts += 1
            if self.attempts == 1:
                raise RuntimeError("temporary transport failure")
            self.delivered.append(notification.id)

    transport = FailOnceTransport()
    async with async_session_factory() as db:
        notification = await NotificationService(db).create(
            user_id,
            type="task_reminder",
            title="Retry me",
            message="Temporary failure test",
            scheduled_at=due,
        )
        service = NotificationService(db, transport=transport)
        with pytest.raises(RuntimeError, match="temporary transport failure"):
            await service.dispatch_scheduled()
        assert await service.dispatch_scheduled() == 1

    assert transport.attempts == 2
    assert transport.delivered == [notification.id]
    async with async_session_factory() as db:
        stored = await db.get(Notification, notification.id)
        assert stored is not None
        assert stored.sent_at is not None


async def test_scheduled_notification_is_hidden_and_not_delivered_early(client):
    user_id, _ = await _register_and_get_id(client, "+919000000420")
    future = datetime.now(UTC) + timedelta(hours=1)
    transport = _RecordingTransport()
    async with async_session_factory() as db:
        notification = await NotificationService(db, transport=transport).create(
            user_id,
            type="task_reminder",
            title="Future reminder",
            message="Not yet",
            scheduled_at=future,
        )
        items, total, unread = await NotificationService(db).list(user_id)
        assert (items, total, unread) == ([], 0, 0)
        assert await NotificationService(db, transport=transport).dispatch_scheduled() == 0

    assert transport.delivered == []
    async with async_session_factory() as db:
        stored = await db.get(Notification, notification.id)
        assert stored is not None
        stored.scheduled_at = datetime.now(UTC) - timedelta(minutes=1)
        await db.commit()
        assert await NotificationService(db, transport=transport).dispatch_scheduled() == 1

    assert transport.delivered == [notification.id]
    async with async_session_factory() as db:
        items, total, unread = await NotificationService(db).list(user_id)
        assert [item.id for item in items] == [notification.id]
        assert (total, unread) == (1, 1)


async def test_notification_idempotency_key_prevents_duplicate_rows(client):
    user_id, _ = await _register_and_get_id(client, "+919000000421")
    async with async_session_factory() as db:
        service = NotificationService(db)
        first = await service.create(
            user_id,
            type="task_reminder",
            title="Reminder",
            message="Once",
            idempotency_key="test-reminder:unique",
        )
        second = await service.create(
            user_id,
            type="task_reminder",
            title="Reminder",
            message="Once",
            idempotency_key="test-reminder:unique",
        )
        assert first.id == second.id
        assert (
            await db.scalar(
                select(func.count()).where(Notification.idempotency_key == "test-reminder:unique")
            )
            == 1
        )


async def test_treatment_followup_handles_sqlite_naive_utc_and_is_idempotent(client):
    user_id, _ = await _register_and_get_id(client, "+919000000423")
    from app.db.seed import seed_catalog

    async with async_session_factory() as db:
        await seed_catalog(db)
        crop = await db.scalar(select(Crop).where(Crop.name == "tomato"))
        assert crop is not None
        scan = Scan(
            client_scan_id=str(uuid.uuid4()),
            user_id=user_id,
            media_items=[],
            image_path="test.jpg",
            crop_id=crop.id,
            disease_name="Leaf spot",
            confidence=0.9,
            provider="test",
            ai_metadata={},
        )
        db.add(scan)
        await db.flush()
        db.add(
            RecoveryLog(
                scan_id=scan.id,
                user_id=user_id,
                treatment_applied="Recorded treatment",
                progress="improving",
                applied_at=(datetime.now(UTC) - timedelta(days=6)).replace(tzinfo=None),
            )
        )
        await db.commit()
        first = await NotificationTriggerService(db).maybe_notify_treatment_reminder(
            user_id, scan.id
        )
        second = await NotificationTriggerService(db).maybe_notify_treatment_reminder(
            user_id, scan.id
        )
        assert first is not None
        assert first.id == second.id
        assert first.payload["next_due_at"].endswith("+00:00")
        assert first.payload["recovery_log_id"] > 0


async def test_system_notifications_dedupe_by_content_not_empty_payload(client):
    user_id, _ = await _register_and_get_id(client, "+919000000424")
    async with async_session_factory() as db:
        triggers = NotificationTriggerService(db)
        first = await triggers.notify_system(user_id, "Notice A", "Message A")
        second = await triggers.notify_system(user_id, "Notice B", "Message B")
        duplicate = await triggers.notify_system(user_id, "Notice A", "Message A")
        assert first is not None and second is not None
        assert duplicate is not None
        assert first.id != second.id
        assert first.id == duplicate.id


async def test_calendar_reminders_use_owned_upcoming_incomplete_tasks(client):
    from app.db.seed import seed_catalog, seed_crop_calendar

    user_id, _ = await _register_and_get_id(client, "+919000000422")
    async with async_session_factory() as db:
        await seed_catalog(db)
        await seed_crop_calendar(db)
        crop = await db.scalar(select(Crop).where(Crop.name == "tomato"))
        assert crop is not None
        schedule = CropSchedule(
            user_id=user_id,
            crop_id=crop.id,
            planting_date=datetime.now(UTC).date(),
        )
        db.add(schedule)
        await db.flush()
        now = datetime.now(UTC)
        due_task = CalendarTask(
            schedule_id=schedule.id,
            kind="watering",
            title="Water crop",
            due_at=now + timedelta(hours=1),
        )
        db.add_all(
            [
                due_task,
                CalendarTask(
                    schedule_id=schedule.id,
                    kind="watering",
                    title="Completed task",
                    due_at=now + timedelta(hours=1),
                    completed_at=now,
                ),
                CalendarTask(
                    schedule_id=schedule.id,
                    kind="watering",
                    title="Outside reminder window",
                    due_at=now + timedelta(days=2),
                ),
            ]
        )
        await db.commit()
        created = await NotificationTriggerService(db).maybe_notify_task_reminder(
            user_id, schedule.id
        )
        repeated = await NotificationTriggerService(db).maybe_notify_task_reminder(
            user_id, schedule.id
        )
        assert len(created) == len(repeated) == 1
        assert created[0].id == repeated[0].id
        assert created[0].payload["task_id"] == due_task.id
        assert (
            await NotificationTriggerService(db).maybe_notify_task_reminder(
                user_id + 1000, schedule.id
            )
            == []
        )


async def test_notification_beat_jobs_are_registered():
    import app.workers.tasks  # noqa: F401
    from app.workers.celery_app import celery_app

    assert (
        celery_app.conf.beat_schedule["dispatch-scheduled-notifications-every-minute"]["task"]
        == "notifications.dispatch_scheduled"
    )
    assert "notifications.dispatch_scheduled" in celery_app.tasks
    assert celery_app.tasks["notifications.dispatch_scheduled"].max_retries == 3
    assert "notifications.create_calendar_reminders" in celery_app.tasks
    assert "notifications.create_treatment_reminders" in celery_app.tasks


# ── Transport interface (push seam) ────────────────────────────────────────


async def test_in_app_transport_is_the_default_noop():
    """Default transport does not raise and records nothing externally."""
    async with async_session_factory() as db:
        notif = await NotificationService(db).create(
            1, type="system", title="hello", message="world"
        )
    assert notif.title == "hello"


# ── Regression ─────────────────────────────────────────────────────────────


async def test_openapi_exposes_notification_endpoints():
    paths = app.openapi()["paths"]
    assert "/api/v1/notifications" in paths
    assert "/api/v1/notifications/unread-count" in paths
    assert "/api/v1/notifications/{notification_id}/read" in paths
    assert "/api/v1/notifications/read-all" in paths
