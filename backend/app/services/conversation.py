"""AI assistant conversation memory (M3.1).

A per-user rolling transcript persisted in ``conversation_messages``. The
service owns the two invariants that make the chat *conversational*:

- **Context window** — the engine only ever sees the last
  :data:`CONTEXT_WINDOW` turns, so follow-up resolution stays fast and bounded.
- **Cap + trim** — the stored transcript is trimmed to :data:`MAX_MESSAGES`
  on every append, so a chat that goes on forever doesn't grow unbounded.

Every turn (user question *and* assistant reply) is stored; assistant turns
also record ``intent`` and ``lang`` so a page reload can restore badges and
voice locale.
"""

from __future__ import annotations

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.conversation import ConversationMessage
from app.schemas.assistant import ConversationMessageOut

# Context window the conversational engine resolves against (oldest-first).
CONTEXT_WINDOW = 20
# Hard cap on the stored transcript (trimmed on append).
MAX_MESSAGES = 60


class ConversationService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def append(
        self,
        user_id: int,
        role: str,
        content: str,
        *,
        intent: str | None = None,
        lang: str | None = None,
    ) -> ConversationMessage:
        """Store one turn and trim the transcript to ``MAX_MESSAGES``."""
        row = ConversationMessage(
            user_id=user_id,
            role=role,
            content=content,
            intent=intent,
            lang=lang,
        )
        self.db.add(row)
        await self.db.flush()
        await self._trim(user_id)
        return row

    async def list(
        self, user_id: int, *, limit: int = CONTEXT_WINDOW
    ) -> list[ConversationMessageOut]:
        """Most recent ``limit`` turns, oldest first (the engine's context window).

        The newest rows are selected by descending time then reversed, so the
        window is the *latest* conversation — follow-ups resolve against what
        was just said, not the chat's opening.
        """
        rows = await self.db.scalars(
            select(ConversationMessage)
            .where(ConversationMessage.user_id == user_id)
            .order_by(ConversationMessage.created_at.desc(), ConversationMessage.id.desc())
            .limit(limit)
        )
        ordered = list(reversed(rows.all()))
        return [
            ConversationMessageOut(
                id=row.id,
                role=row.role,
                content=row.content,
                intent=row.intent,
                lang=row.lang,
                created_at=row.created_at,
            )
            for row in ordered
        ]

    async def clear(self, user_id: int) -> None:
        """Drop the user's entire transcript (clear-chat)."""
        await self.db.execute(
            delete(ConversationMessage).where(ConversationMessage.user_id == user_id)
        )

    async def _trim(self, user_id: int) -> None:
        """Keep only the newest ``MAX_MESSAGES`` rows for the user."""
        keep = select(ConversationMessage.id)
        keep = (
            keep.where(ConversationMessage.user_id == user_id)
            .order_by(ConversationMessage.created_at.desc(), ConversationMessage.id.desc())
            .limit(MAX_MESSAGES)
        )
        await self.db.execute(
            delete(ConversationMessage).where(
                ConversationMessage.user_id == user_id,
                ConversationMessage.id.not_in(keep),
            )
        )
