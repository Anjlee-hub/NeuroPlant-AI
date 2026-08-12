"""Notification schemas (M5, Task 2).

Request/response DTOs for the in-app notification foundation. The ``type``
vocabulary is validated at the boundary (namespace of stable keys from
:class:`app.models.notification.NotificationType`); ownership and read-state
mutations live in :mod:`app.services.notifications`.

Listing is paginated with a total/count envelope so the client can render
pagers without a second call. Title/message length limits are enforced here so
a single long notification can't bloat the wire or the DB column.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.notification import NotificationType

# Boundary limits (mirrored by the migration column sizes).
TITLE_MAX_LENGTH = 200
MESSAGE_MAX_LENGTH = 2000

# Pagination defaults (shared with the marketplace/reviews services).
DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100

# Accepted ``type`` values (validated against the enum at the boundary).
NOTIFICATION_TYPES = tuple(t.value for t in NotificationType)


class NotificationOut(BaseModel):
    """One notification as returned by list / mark-read endpoints."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    type: str = Field(description="notification type key, e.g. 'weather_risk'")
    title: str
    message: str
    payload: dict = Field(default_factory=dict)
    read_at: datetime | None = None
    scheduled_at: datetime | None = None
    created_at: datetime


class NotificationPageOut(BaseModel):
    """Paginated notification listing for the authenticated user."""

    items: list[NotificationOut] = Field(default_factory=list)
    total: int = Field(ge=0)
    unread: int = Field(ge=0)
    page: int = Field(ge=1)
    page_size: int = Field(ge=1)
    pages: int = Field(ge=0)


class UnreadCountOut(BaseModel):
    """GET /notifications/unread-count — the user's current unread total."""

    unread: int = Field(ge=0)


class MarkReadOut(BaseModel):
    """Response for mark-one / mark-all read — the count just changed."""

    updated: int = Field(ge=0, description="Number of notifications marked read")
