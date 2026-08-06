"""Voice AI assistant endpoint (M3 Task 6 → M3.1 conversational upgrade).

A thin HTTP wrapper over :class:`AssistantService`: the router does *no* policy —
the service resolves intent, composes the existing engines, and localizes the
reply. A user asking about a scan, treatment, fertilizer, soil, recovery or
calendar reminder always gets a structured reply (never a 500): the service
degrades missing data to a helpful message.

M3.1 adds ``GET/DELETE /assistant/conversation`` so the frontend can restore the
chat history on page load and clear it on demand.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.assistant import (
    AssistantIn,
    AssistantReplyOut,
    ConversationOut,
)
from app.services.assistant import AssistantService

router = APIRouter(prefix="/assistant", tags=["assistant"])

Db = Annotated[AsyncSession, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]


@router.post("", response_model=AssistantReplyOut)
async def ask_assistant(payload: AssistantIn, user: CurrentUser, db: Db) -> AssistantReplyOut:
    """Answer one farming question from the user's own farm data.

    ``lang`` is optional — the service detects it from the query's script when
    omitted (Devanagari → Hindi). The reply is always structured and localized;
    the frontend renders the bubble + sections and may read them aloud via TTS.
    The turn is persisted so follow-ups keep context across requests.
    """
    return await AssistantService(db).answer(user, payload.query, payload.lang)


@router.get("/conversation", response_model=ConversationOut)
async def get_conversation(user: CurrentUser, db: Db) -> ConversationOut:
    """The user's recent chat transcript, oldest first (for history restore)."""
    return await AssistantService(db).conversation(user)


@router.delete("/conversation", status_code=status.HTTP_204_NO_CONTENT)
async def clear_conversation(user: CurrentUser, db: Db) -> None:
    """Clear the user's entire chat transcript (clear-chat)."""
    await AssistantService(db).clear_conversation(user)
