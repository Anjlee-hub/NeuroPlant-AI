"""Notification endpoints (M5, Task 2).

Four routes under ``/notifications`` cover the in-app notification foundation:

* **GET** ``""`` — paginated list for the authenticated user (newest first).
* **GET** ``/unread-count`` — total unread count for the current user.
* **PATCH** ``/{id}/read`` — mark one notification as read.
* **PATCH** ``/read-all`` — mark all unread notifications as read.

All routes require authentication; ownership is enforced in the service
(enumeration guard: missing/foreign ids answer 404). No push is implemented —
the client polls the list endpoint. Creation is NOT exposed via HTTP; domain
services (weather risk, calendar, marketplace, etc.) call the service directly.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.notification import (
    DEFAULT_PAGE_SIZE,
    MAX_PAGE_SIZE,
    MarkReadOut,
    NotificationPageOut,
    UnreadCountOut,
)
from app.services.notifications import NotificationService

router = APIRouter(prefix="/notifications", tags=["notifications"])

Db = Annotated[AsyncSession, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]


@router.get("", response_model=NotificationPageOut)
async def list_notifications(
    user: CurrentUser,
    db: Db,
    page: Annotated[int, Query(ge=1, description="Page number")] = 1,
    page_size: Annotated[
        int,
        Query(ge=1, le=MAX_PAGE_SIZE, description="Items per page"),
    ] = DEFAULT_PAGE_SIZE,
) -> NotificationPageOut:
    """Paginated list of notifications for the authenticated user (newest first)."""
    items, total, unread = await NotificationService(db).list(user.id, page, page_size)
    pages = (total + page_size - 1) // page_size if total else 0
    return NotificationPageOut(
        items=items,
        total=total,
        unread=unread,
        page=page,
        page_size=page_size,
        pages=pages,
    )


@router.get("/unread-count", response_model=UnreadCountOut)
async def get_unread_count(user: CurrentUser, db: Db) -> UnreadCountOut:
    """Total unread notifications for the authenticated user."""
    unread = await NotificationService(db).unread_count(user.id)
    return UnreadCountOut(unread=unread)


@router.patch("/{notification_id}/read", response_model=MarkReadOut)
async def mark_notification_read(
    notification_id: int,
    user: CurrentUser,
    db: Db,
) -> MarkReadOut:
    """Mark one notification as read. 404 if not owned by the user."""
    await NotificationService(db).mark_read(user.id, notification_id)
    return MarkReadOut(updated=1)


@router.patch("/read-all", response_model=MarkReadOut)
async def mark_all_notifications_read(user: CurrentUser, db: Db) -> MarkReadOut:
    """Mark all unread notifications as read. Returns the number updated."""
    updated = await NotificationService(db).mark_all_read(user.id)
    return MarkReadOut(updated=updated)