"""Marketplace buyer↔seller messaging endpoints (M4, Task 5).

Six routes under ``/marketplace/conversations`` cover the inquiry system:

* **POST** ``""`` — start (or reuse) a thread from a seller / listing / product.
* **GET** ``""`` — the caller's inbox (both sides, newest activity first).
* **GET** ``/{id}`` — one full thread (participants only).
* **POST** ``/{id}/messages`` — send one message.
* **POST** ``/{id}/read`` — mark the other side's messages as read.
* **POST** ``/{id}/close`` — close the thread (idempotent).

Every route requires an authenticated user; ownership is enforced in the
service, which answers ``404`` for threads the caller doesn't belong to (the
platform's enumeration guard). Message writes are rate-limited per user+IP.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_current_user, message_rate_limit
from app.db.session import get_db
from app.models.user import User
from app.schemas.messaging import (
    ConversationCreate,
    ConversationDetailOut,
    ConversationListItemOut,
    MessageIn,
    MessageOut,
    ReadResultOut,
)
from app.services.messaging import MessagingService

router = APIRouter(prefix="/marketplace/conversations", tags=["marketplace"])

Db = Annotated[AsyncSession, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]


@router.post(
    "",
    response_model=ConversationDetailOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_conversation(
    payload: ConversationCreate,
    user: CurrentUser,
    db: Db,
    _rate: None = Depends(message_rate_limit),
) -> ConversationDetailOut:
    """Start (or reuse) a conversation with a seller or listing farmer."""
    return await MessagingService(db).create_conversation(user, payload)


@router.get("", response_model=list[ConversationListItemOut])
async def list_conversations(user: CurrentUser, db: Db) -> list[ConversationListItemOut]:
    """Every conversation the caller participates in (buyer or seller side)."""
    return await MessagingService(db).list_conversations(user)


@router.get("/{conversation_id}", response_model=ConversationDetailOut)
async def get_conversation(
    conversation_id: int, user: CurrentUser, db: Db
) -> ConversationDetailOut:
    """One full thread — participants only (anyone else gets 404)."""
    return await MessagingService(db).detail(user, conversation_id)


@router.post(
    "/{conversation_id}/messages",
    response_model=MessageOut,
    status_code=status.HTTP_201_CREATED,
)
async def send_message(
    conversation_id: int,
    payload: MessageIn,
    user: CurrentUser,
    db: Db,
    _rate: None = Depends(message_rate_limit),
) -> MessageOut:
    """Append one message; rejected (409) once the conversation is closed."""
    return await MessagingService(db).send_message(user, conversation_id, payload)


@router.post("/{conversation_id}/read", response_model=ReadResultOut)
async def mark_read(conversation_id: int, user: CurrentUser, db: Db) -> ReadResultOut:
    """Mark the other side's messages as read for the caller."""
    return await MessagingService(db).mark_read(user, conversation_id)


@router.post("/{conversation_id}/close", response_model=ConversationListItemOut)
async def close_conversation(
    conversation_id: int, user: CurrentUser, db: Db
) -> ConversationListItemOut:
    """Close the conversation (idempotent; history stays visible)."""
    return await MessagingService(db).close(user, conversation_id)
