# M5 Task 2: Notifications Foundation — Completion Report

**Date:** 2026-08-12  
**Commit:** (to be created)  
**Branch:** main

---

## Summary

Implemented the in-app notification foundation for NeuroPlant AI. This provides a user-scoped, paginated notification system with read-state management, a transport interface for future push providers (FCM, APNs, Web Push), and a scheduling seam for Celery beat integration. Creation is decoupled from HTTP — domain services (weather risk, calendar, marketplace, etc.) call the service directly.

---

## Files Added / Modified

| File | Status | Purpose |
|------|--------|---------|
| `app/models/notification.py` | Added | Notification model + `NotificationType` enum (11 types) |
| `alembic/versions/e1b2c3d4f5a6_add_notifications.py` | Added | Migration with Postgres enum + SQLite fallback, indexes |
| `app/schemas/notification.py` | Added | Request/response DTOs, constants, validation |
| `app/services/notifications.py` | Added | Service + `NotificationTransport` protocol + exceptions |
| `app/api/v1/endpoints/notifications.py` | Added | 4 endpoints: list, unread-count, mark-read, mark-all-read |
| `app/main.py` | Modified | Exception handlers for `NotificationNotFoundError` (404) and `NotificationValidationError` (400) |
| `tests/test_notifications.py` | Added | 27 tests covering auth, service, list pagination, unread count, mark read, scheduling, transport, OpenAPI |

---

## Notification Types (11)

| Enum Value | Use Case |
|------------|----------|
| `weather_risk` | Heavy rain, frost, heat warnings |
| `disease_risk` | Pathogen risk crossing threshold |
| `treatment_reminder` | Scheduled spray/fertilizer due |
| `task_reminder` | Calendar task due (harvest, scout, etc.) |
| `outbreak_alert` | Regional disease outbreak |
| `yield_prediction` | New yield forecast available |
| `price_alert` | Market price crossed threshold |
| `marketplace_message` | Buyer↔seller chat message |
| `review_received` | New review on listing/product |
| `order_update` | Order status change |
| `system` | Maintenance, feature announcements |

---

## API Endpoints (all require auth, ownership enforced)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/notifications` | Paginated list (newest first), query: `page`, `page_size` |
| GET | `/api/v1/notifications/unread-count` | Total unread for current user |
| PATCH | `/api/v1/notifications/{id}/read` | Mark one as read (idempotent) |
| PATCH | `/api/v1/notifications/read-all` | Mark all unread as read |

**Response envelope (list):** `{ items, total, unread, page, page_size, pages }`

**Defaults:** `DEFAULT_PAGE_SIZE=20`, `MAX_PAGE_SIZE=100` (shared with marketplace/reviews).

---

## Service Layer

### `NotificationService(db, transport?)`
- `list(user_id, page, page_size)` → `(items, total, unread)`
- `unread_count(user_id)` → `int`
- `mark_read(user_id, notification_id)` → `Notification` (404 if not owned)
- `mark_all_read(user_id)` → `int` (count updated)
- `create(user_id, type, title, message, payload?, scheduled_at?)` → `Notification`
- `dispatch_scheduled(limit=100)` → `int` (sent_at set after delivery)

### Transport Interface (push seam)
```python
class NotificationTransport(Protocol):
    async def send(self, user: User, notification: Notification) -> None: ...

class InAppTransport:  # default, no-op
    async def send(self, user, notification): ...
```
Real providers (FCM, APNs, Web Push, email, SMS) implement the protocol and are injected at app startup.

### Scheduling Seam
- `scheduled_at` = when the notification should be delivered (future)
- `sent_at` = set by `dispatch_scheduled` after transport delivers
- `read_at` = set by user action (separate from delivery)
- Celery beat will call `dispatch_scheduled()` periodically

---

## Migration Details

- **Postgres:** native enum `notificationtype` + `JSONB` payload
- **SQLite:** `TEXT` enum + `TEXT` payload (JSON serialized)
- **Indexes:**
  - `ix_notifications_user_read` on `(user_id, read_at)` — unread queries
  - `ix_notifications_user_scheduled` on `(user_id, scheduled_at)` — scheduler
  - `ix_notifications_user_created` on `(user_id, created_at)` — list pagination
  - `ix_notifications_type` on `type` — analytics/filtering

Alembic head: `e1b2c3d4f5a6` (single head)

---

## Test Coverage (27 tests)

| Category | Tests |
|----------|-------|
| Authentication | 1 (all 4 endpoints → 401) |
| Service creation / validation | 4 (enum/string type, invalid type, blank title/message, scheduled_at) |
| List pagination / unread | 5 (user scoping, pagination limits, newest-first, unread count) |
| Mark one read | 3 (idempotent, cross-user 404, missing 404) |
| Mark all read | 3 (returns count, user-scoped, idempotent) |
| Scheduling seam | 2 (dispatches due only, no repeat) |
| Transport interface | 1 (default no-op) |
| OpenAPI regression | 1 (all 4 routes present) |

---

## Quality Gates

| Gate | Status |
|------|--------|
| `pytest` (backend) | ✅ 456 passed, 1 skipped, 80% coverage |
| `ruff check` | ✅ clean |
| `ruff format --check` | ✅ clean |
| `mypy app` | ✅ Success: no issues found in 100 source files |
| `pip check` | ✅ No broken requirements |

---

## Integration Notes

- **No HTTP creation endpoint** — domain services call `NotificationService.create()` directly.
- **Enumeration guard** — cross-user / missing IDs return 404 (consistent with scans, soil, recovery, messaging, favorites, reviews).
- **No push implemented** — client polls `/notifications`. Transport protocol ready for FCM/APNs/Web Push.
- **Scheduled notifications** — `dispatch_scheduled()` is a seam; no background worker runs today.

---

## Next Steps (M5 Task 3)

Wire the notification service into domain triggers:
- Weather risk → `weather_risk` / `disease_risk` notifications
- Calendar → `task_reminder` / `treatment_reminder`
- Marketplace messages → `marketplace_message`
- Reviews → `review_received`
- Orders → `order_update`
- System announcements → `system`

This will be M5 Task 3: "Notification Triggers & Integration".