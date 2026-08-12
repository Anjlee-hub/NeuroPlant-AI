"""Notification model (M5, Task 2).

In-app notifications with user ownership, typed payloads, and a scheduling
seam for future scheduled reminders. Push transports are NOT implemented here;
the :class:`NotificationTransport` protocol in :mod:`app.services.notifications`
is the seam where a real provider plugs in later.

The table is intentionally independent from weather/disease-risk logic — it
stores whatever the caller enqueues, keyed by a stable ``type`` enum so
clients can group/filter without coupling to domain modules.
"""

from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import DateTime, ForeignKey, Index, Integer, JSON, String, Text, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base
from app.models.base import TimestampMixin


class NotificationType(str, PyEnum):
    """Stable type keys for client grouping/filtering.

    These are the M5+ types needed across milestones. They are decoupled from
    any domain module — the service that *creates* a notification decides which
    type to use and what ``payload`` to attach. The notification table itself
    only enforces the enum.
    """

    WEATHER_RISK = "weather_risk"
    DISEASE_RISK = "disease_risk"
    TREATMENT_REMINDER = "treatment_reminder"
    TASK_REMINDER = "task_reminder"
    OUTBREAK_ALERT = "outbreak_alert"
    YIELD_PREDICTION = "yield_prediction"
    PRICE_ALERT = "price_alert"
    MARKETPLACE_MESSAGE = "marketplace_message"
    REVIEW_RECEIVED = "review_received"
    ORDER_UPDATE = "order_update"
    SYSTEM = "system"


class Notification(Base, TimestampMixin):
    """One in-app notification for a user.

    ``read_at`` is NULL when unread; setting it marks the notification read.
    ``scheduled_at`` is the seam for future scheduled reminders (e.g. a
    treatment reminder the day before a calendar task) — it is NOT consumed by
    any background worker today. When a scheduler arrives (Celery beat or
    similar), it will query ``WHERE scheduled_at <= now() AND sent_at IS NULL``
    and set ``sent_at`` after delivery.
    """

    __tablename__ = "notifications"
    __table_args__ = (
        Index("ix_notifications_user_unread", "user_id", "read_at"),
        Index("ix_notifications_user_scheduled", "user_id", "scheduled_at"),
        Index("ix_notifications_user_created", "user_id", "created_at"),
        Index("ix_notifications_type", "type"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    type: Mapped[NotificationType] = mapped_column(
        SAEnum(NotificationType, name="notification_type"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)