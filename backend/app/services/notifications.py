"""Notification service + transport interface + scheduling seam (M5, Task 2).

Ownership: every notification belongs to exactly one user; the service
enforces this by filtering every query with ``user_id`` and answering ``404``
for ids the caller doesn't own (enumeration guard, consistent with
scans/soil/recovery/messaging).

Transport: push is NOT implemented. :class:`NotificationTransport` is a
protocol so a real provider (FCM, APNs, Web Push, email, SMS) can be injected
later. The default :class:`InAppTransport` is a no-op — notifications persist
in the DB and the client polls ``/notifications``.

Scheduling: ``scheduled_at`` is a seam for future scheduled reminders (e.g. a
treatment reminder the day before a calendar task). No background worker
consumes it today. When Celery beat or similar arrives, it will query
``WHERE scheduled_at <= now() AND sent_at IS NULL`` and call
:meth:`NotificationService.dispatch_scheduled` which will set ``sent_at`` after
delivery. ``sent_at`` is separate from ``read_at`` so a notification can be
delivered (sent) but still unread.

Creation is decoupled from weather/disease-risk: callers pass
``type`` + ``title`` + ``message`` + optional ``payload``. The domain service
that knows *when* to notify (weather risk crossing a threshold, a calendar
task due, etc.) is the one that calls :meth:`NotificationService.create` —
the notification layer knows nothing about weather or disease rules.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.notification import Notification, NotificationType
from app.models.user import User

logger = get_logger(__name__)


# ── Constants (shared with API layer) ──────────────────────────────────────

DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100


# ── Transport interface (push seam) ──────────────────────────────────────


class NotificationTransport(Protocol):
    """Anything that can deliver a notification to a user.

    Implementations will be injected by the application when a real provider
    (FCM, APNs, Web Push, email, SMS) is configured. The default
    :class:`InAppTransport` does nothing — the notification stays in the DB
    and the client polls the list endpoint.
    """

    async def send(self, user: User, notification: Notification) -> None: ...


class InAppTransport:
    """Default transport — no push, client polls ``/notifications``."""

    async def send(self, user: User, notification: Notification) -> None:
        # No-op: in-app only. The row is already in the DB.
        logger.debug("in_app_notification", user_id=user.id, notification_id=notification.id)


# ── Domain exceptions (mapped to HTTP in ``app.main``) ─────────────────────


class NotificationNotFoundError(Exception):
    """The requested notification doesn't exist or doesn't belong to the user."""


class NotificationValidationError(Exception):
    """Input failed validation (bad type, missing fields, etc.)."""


# ── Service ────────────────────────────────────────────────────────────────


@dataclass
class _PaginationResult:
    items: list[Notification]
    total: int
    unread: int


class NotificationService:
    """In-app notification CRUD + read-state mutations + scheduling seam."""

    def __init__(
        self,
        db: AsyncSession,
        transport: NotificationTransport | None = None,
    ) -> None:
        self.db = db
        self.transport = transport or InAppTransport()

    # ── List / count ──────────────────────────────────────────────────────

    async def list(
        self,
        user_id: int,
        page: int = 1,
        page_size: int = DEFAULT_PAGE_SIZE,
    ) -> tuple[list[Notification], int, int]:
        """Paginated list for a user, newest first, with total + unread count."""
        page_size = max(1, min(page_size, MAX_PAGE_SIZE))
        page = max(1, page)

        base = select(Notification).where(Notification.user_id == user_id)
        total = (await self.db.scalar(select(func.count()).select_from(base.subquery()))) or 0
        unread = (
            await self.db.scalar(
                select(func.count()).where(
                    Notification.user_id == user_id, Notification.read_at.is_(None)
                )
            )
        ) or 0

        items = (
            await self.db.execute(
                base.order_by(Notification.created_at.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
        ).scalars().all()

        return list(items), total, unread

    async def unread_count(self, user_id: int) -> int:
        """Total unread notifications for a user."""
        return (
            await self.db.scalar(
                select(func.count()).where(
                    Notification.user_id == user_id, Notification.read_at.is_(None)
                )
            )
        ) or 0

    # ── Mark read ─────────────────────────────────────────────────────────

    async def mark_read(self, user_id: int, notification_id: int) -> Notification:
        """Mark one notification as read. 404 if not owned by the user."""
        notif = await self._get_owned(notification_id, user_id)
        if notif.read_at is None:
            notif.read_at = datetime.now(UTC)
            await self.db.commit()
        return notif

    async def mark_all_read(self, user_id: int) -> int:
        """Mark all unread notifications as read. Returns the number updated."""
        now = datetime.now(UTC)
        result = await self.db.execute(
            select(Notification).where(
                Notification.user_id == user_id, Notification.read_at.is_(None)
            )
        )
        unread = result.scalars().all()
        for n in unread:
            n.read_at = now
        await self.db.commit()
        return len(unread)

    # ── Creation (called by domain services, not HTTP) ────────────────────

    async def create(
        self,
        user_id: int,
        *,
        type: NotificationType | str,
        title: str,
        message: str,
        payload: dict | None = None,
        scheduled_at: datetime | None = None,
    ) -> Notification:
        """Enqueue a notification for a user.

        Validation:
        - ``type`` must be a valid ``NotificationType`` key (validated at the
          boundary in the API; this method accepts the enum or the raw string).
        - ``title`` and ``message`` non-empty.
        - ``payload`` serializable dict (default empty).
        - ``scheduled_at`` optional; if set, ``sent_at`` will be set by the
          future scheduler after dispatch.
        """
        if isinstance(type, str):
            try:
                type_enum = NotificationType(type)
            except ValueError as exc:
                raise NotificationValidationError(
                    f"Invalid notification type: {type}. Allowed: {[t.value for t in NotificationType]}"
                ) from exc
        else:
            type_enum = type

        if not title or not title.strip():
            raise NotificationValidationError("title must not be empty")
        if not message or not message.strip():
            raise NotificationValidationError("message must not be empty")

        notif = Notification(
            user_id=user_id,
            type=type_enum,
            title=title.strip(),
            message=message.strip(),
            payload=payload or {},
            scheduled_at=scheduled_at,
        )
        self.db.add(notif)
        await self.db.flush()

        # Fire-and-forget in-app transport (no-op today, real provider later).
        # ``send`` may be called again by the scheduler when ``scheduled_at`` fires.
        user = await self.db.get(User, user_id)
        if user:
            await self.transport.send(user, notif)
        await self.db.commit()

        logger.info(
            "notification_created",
            user_id=user_id,
            notification_id=notif.id,
            type=type_enum.value,
            scheduled=scheduled_at.isoformat() if scheduled_at else None,
        )
        return notif

    # ── Scheduling seam (future Celery beat consumer) ─────────────────────

    async def dispatch_scheduled(self, limit: int = 100) -> int:
        """Dispatch notifications whose ``scheduled_at`` has passed.

        This is the seam a Celery beat task will call periodically (e.g. every
        minute). It finds notifications with ``scheduled_at <= now() AND
        sent_at IS NULL``, sends them via the transport, and sets ``sent_at``.
        Returns the number dispatched.

        ``limit`` protects against runaway batches if the scheduler falls behind.
        """
        now = datetime.now(UTC)
        result = await self.db.execute(
            select(Notification).where(
                Notification.scheduled_at <= now, Notification.sent_at.is_(None)
            ).limit(limit)
        )
        scheduled = result.scalars().all()

        dispatched = 0
        for notif in scheduled:
            user = await self.db.get(User, notif.user_id)
            if user:
                await self.transport.send(user, notif)
            notif.sent_at = now
            dispatched += 1

        if dispatched:
            await self.db.commit()
            logger.info("scheduled_notifications_dispatched", count=dispatched)
        return dispatched

    # ── Internal helpers ──────────────────────────────────────────────────

    async def _get_owned(self, notification_id: int, user_id: int) -> Notification:
        notif = await self.db.get(Notification, notification_id)
        if notif is None or notif.user_id != user_id:
            raise NotificationNotFoundError(
                f"Notification {notification_id} not found."
            )
        return notif