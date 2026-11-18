
"""Notification service + transport interface + scheduling seam (M5, Task 2).

Ownership: every notification belongs to exactly one user; the service
enforces this by filtering every query with ``user_id`` and answering ``404``
for ids the caller doesn't own.

Transport: push is NOT implemented. NotificationTransport is a protocol
so a real provider can be injected later. The default InAppTransport is a
no-op — notifications persist in the DB and the client polls /notifications.

Scheduling: scheduled_at holds future deliveries. Celery beat calls
NotificationService.dispatch_scheduled, which only delivers due rows and
sets sent_at after successful delivery.

Creation is decoupled from weather/disease-risk: callers pass type, title,
message and optional payload.
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


DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100


class NotificationTransport(Protocol):
    """Interface for notification delivery providers."""

    async def send(self, user: User, notification: Notification) -> None: ...


class InAppTransport:
    """Default transport — client polls /notifications."""

    async def send(self, user: User, notification: Notification) -> None:
        logger.debug(
            "in_app_notification",
            user_id=user.id,
            notification_id=notification.id,
        )


class NotificationNotFoundError(Exception):
    """Notification does not exist or does not belong to the user."""


class NotificationValidationError(Exception):
    """Input failed notification validation."""


@dataclass
class _PaginationResult:
    items: list[Notification]
    total: int
    unread: int


class NotificationService:
    """In-app notification CRUD, read-state mutations and scheduling."""

    def __init__(
        self,
        db: AsyncSession,
        transport: NotificationTransport | None = None,
    ) -> None:
        self.db = db
        self.transport = transport or InAppTransport()

    async def list(
        self,
        user_id: int,
        page: int = 1,
        page_size: int = DEFAULT_PAGE_SIZE,
    ) -> tuple[list[Notification], int, int]:
        """Return a paginated list for a user, newest first."""
        page_size = max(1, min(page_size, MAX_PAGE_SIZE))
        page = max(1, page)

        visible = or_(
            Notification.scheduled_at.is_(None),
            Notification.sent_at.is_not(None),
        )
        base = select(Notification).where(
            Notification.user_id == user_id,
            visible,
        )

        total = (
            await self.db.scalar(
                select(func.count()).select_from(base.subquery())
            )
        ) or 0

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
        """Return the total number of unread visible notifications."""
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

    async def mark_read(
        self,
        user_id: int,
        notification_id: int,
    ) -> Notification:
        """Mark one notification as read. Raise 404 if not owned."""
        notif = await self._get_owned(notification_id, user_id)

        if notif.read_at is None:
            notif.read_at = datetime.now(UTC)
            await self.db.commit()

        return notif

    async def mark_all_read(self, user_id: int) -> int:
        """Mark all visible unread notifications as read."""
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

        for notification in unread:
            notification.read_at = now

        await self.db.commit()
        return len(unread)

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
        """Create a notification for a user."""
        if isinstance(type, str):
            try:
                type_enum = NotificationType(type)
            except ValueError as exc:
                allowed_types = [
                    notification_type.value
                    for notification_type in NotificationType
                ]
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
                select(Notification).where(
                    Notification.idempotency_key == idempotency_key
                )
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
                select(Notification).where(
                    Notification.idempotency_key == idempotency_key
                )
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

    async def dispatch_scheduled(self, limit: int = 100) -> int:
        """Deliver due scheduled notifications and mark successful deliveries."""
        now = datetime.now(UTC)
        dispatched = 0

        while dispatched < limit:
            result = await self.db.execute(
                select(Notification)
                .where(
                    Notification.scheduled_at <= now,
                    Notification.sent_at.is_(None),
                )
                .order_by(
                    Notification.scheduled_at,
                    Notification.id,
                )
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
            logger.info(
                "scheduled_notifications_dispatched",
                count=dispatched,
            )

        return dispatched

    async def _get_owned(
        self,
        notification_id: int,
        user_id: int,
    ) -> Notification:
        """Get a visible notification owned by the specified user."""
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
            raise NotificationNotFoundError(
                f"Notification {notification_id} not found."
            )

        return notif
