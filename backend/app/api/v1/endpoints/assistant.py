"""Voice AI assistant endpoint (M3, Task 6).

A thin HTTP wrapper over :class:`AssistantService`: the router does *no* policy —
the service detects intent, composes the existing engines, and localizes the
reply. A user asking about a scan, treatment, fertilizer, soil, recovery or
calendar reminder always gets a structured reply (never a 500): the service
degrades missing data to a helpful message.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.assistant import AssistantIn, AssistantReplyOut
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
    """
    return await AssistantService(db).answer(user, payload.query, payload.lang)
