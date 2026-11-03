"""Notification service + transport interface + scheduling seam (M5, Task 2).

Ownership: every notification belongs to exactly one user; the service
enforces this by filtering every query with ``user_id`` and answering ``404``
for ids the caller doesn't own (enumeration guard, consistent with
scans/soil/recovery/messaging).

Transport: push is NOT implemented. :class:`NotificationTransport` is a
protocol so a real provider (FCM, APNs, Web Push, email, SMS) can be injected
later. The default :class:`InAppTransport` is a no-op — notifications persist
in the DB and the client polls ``/notifications``.

Scheduling: ``scheduled_at`` holds future deliveries. Celery beat calls
:meth:`NotificationService.dispatch_scheduled`, which only delivers due rows
and sets ``sent_at`` after successful delivery. ``sent_at`` is separate from
``read_at`` so a notification can be delivered but still unread.

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

from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
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

        visible = or_(
            Notification.scheduled_at.is_(None),
            Notification.sent_at.is_not(None),
        )
        base = select(Notification).where(Notification.user_id == user_id, visible)
        total = (await self.db.scalar(select(func.count()).select_from(base.subquery()))) or 0
        unread = (
            await self.db.scalar(
                select(func.count()).where(
                    Notification.user_id == user_id,
                    Notification.read_at.is_(None),
                    visible,
                )
            )
        ) or 0

        items = (
            (
                await self.db.execute(
                    base.order_by(Notification.created_at.desc())
                    .offset((page - 1) * page_size)
                    .limit(page_size)
                )
            )
            .scalars()
            .all()
        )

        return list(items), total, unread

    async def unread_count(self, user_id: int) -> int:
        """Total unread notifications for a user."""
        return (
            await self.db.scalar(
                select(func.count()).where(
                    Notification.user_id == user_id,
                    Notification.read_at.is_(None),
                    or_(
                        Notification.scheduled_at.is_(None),
                        Notification.sent_at.is_not(None),
                    ),
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
                Notification.user_id == user_id,
                Notification.read_at.is_(None),
                or_(
                    Notification.scheduled_at.is_(None),
                    Notification.sent_at.is_not(None),
                ),
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
        idempotency_key: str | None = None,
    ) -> Notification:
        """Enqueue a notification for a user.

        Validation:
        - ``type`` must be a valid ``NotificationType`` key (validated at the
          boundary in the API; this method accepts the enum or the raw string).
        - ``title`` and ``message`` non-empty.
        - ``payload`` serializable dict (default empty).
        - ``scheduled_at`` optional; if set, ``sent_at`` is set after the
          Celery dispatcher delivers it.
        """
        if isinstance(type, str):
            try:
                type_enum = NotificationType(type)
            except ValueError as exc:
                allowed_types = [notification_type.value for notification_type in NotificationType]
                raise NotificationValidationError(
                    f"Invalid notification type: {type}. Allowed: {allowed_types}"
                ) from exc
        else:
            type_enum = type

        if not title or not title.strip():
            raise NotificationValidationError("title must not be empty")
        if not message or not message.strip():
            raise NotificationValidationError("message must not be empty")

        if idempotency_key is not None:
            existing = await self.db.scalar(
                select(Notification).where(Notification.idempotency_key == idempotency_key)
            )
            if existing is not None:
                return existing

        notif = Notification(
            user_id=user_id,
            type=type_enum,
            title=title.strip(),
            message=message.strip(),
            payload=payload or {},
            scheduled_at=scheduled_at,
            idempotency_key=idempotency_key,
        )
        self.db.add(notif)
        await self.db.flush()

        try:
            # Scheduled notifications stay hidden and undelivered until the
            # scheduler claims them after their scheduled time.
            if scheduled_at is None:
                user = await self.db.get(User, user_id)
                if user:
                    await self.transport.send(user, notif)
            await self.db.commit()
        except IntegrityError:
            await self.db.rollback()
            if idempotency_key is None:
                raise
            existing = await self.db.scalar(
                select(Notification).where(Notification.idempotency_key == idempotency_key)
            )
            if existing is None:
                raise
            return existing

        logger.info(
            "notification_created",
            user_id=user_id,
            notification_id=notif.id,
            type=type_enum.value,
            scheduled=scheduled_at.isoformat() if scheduled_at else None,
        )
        return notif

    # ── Scheduled delivery (consumed by Celery Beat) ─────────────────────

    async def dispatch_scheduled(self, limit: int = 100) -> int:
        """Dispatch notifications whose ``scheduled_at`` has passed.

        Celery Beat calls this periodically (every minute). It finds
        notifications with ``scheduled_at <= now() AND
        sent_at IS NULL``, sends them via the transport, and sets ``sent_at``.
        Returns the number dispatched.

        ``limit`` protects against runaway batches if the scheduler falls behind.
        Row-level locks prevent concurrent workers from claiming the same rows
        on databases that support ``SKIP LOCKED``.
        """
        now = datetime.now(UTC)
        dispatched = 0
        while dispatched < limit:
            result = await self.db.execute(
                select(Notification)
                .where(Notification.scheduled_at <= now, Notification.sent_at.is_(None))
                .order_by(Notification.scheduled_at, Notification.id)
                .limit(1)
                .with_for_update(skip_locked=True)
            )
            notif = result.scalar_one_or_none()
            if notif is None:
                break

            user = await self.db.get(User, notif.user_id)
            if user is None:
                await self.db.rollback()
                break

            try:
                await self.transport.send(user, notif)
                notif.sent_at = now
                await self.db.commit()
            except Exception:
                await self.db.rollback()
                raise
            dispatched += 1

        if dispatched:
            logger.info("scheduled_notifications_dispatched", count=dispatched)
        return dispatched

    # ── Internal helpers ──────────────────────────────────────────────────

    async def _get_owned(self, notification_id: int, user_id: int) -> Notification:
        notif = await self.db.scalar(
            select(Notification).where(
                Notification.id == notification_id,
                Notification.user_id == user_id,
                or_(
                    Notification.scheduled_at.is_(None),
                    Notification.sent_at.is_not(None),
                ),
            )
        )
        if notif is None:
            raise NotificationNotFoundError(f"Notification {notification_id} not found.")
        return notif
