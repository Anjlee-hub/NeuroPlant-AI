"""AI assistant facade (M3.1).

Thin orchestration layer — all policy lives in the conversation providers
(:mod:`app.services.assistant_providers`) and the engine services they compose.
``AssistantService`` only:

1. resolves the reply language (client preference, else script detection),
2. loads the rolling transcript (:class:`ConversationService`),
3. delegates to the active provider (local engine or LLM),
4. persists the turn (user + assistant) so a page reload restores the chat,
5. returns the structured, localized reply.

The same service also backs ``GET/DELETE /assistant/conversation`` so the
frontend can restore the chat history and clear it.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.user import User
from app.schemas.assistant import AssistantReplyOut, ConversationOut
from app.services.assistant_context import ASSISTANT_LANGS, AssistantContext, detect_lang
from app.services.assistant_providers import (
    ConversationProvider,
    LocalConversationProvider,
    select_conversation_provider,
)
from app.services.conversation import ConversationService

logger = get_logger(__name__)


class AssistantService:
    """Answer farmer questions by composing the existing engine services."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self._provider: ConversationProvider = select_conversation_provider(db)

    async def answer(self, user: User, query: str, lang: str | None = None) -> AssistantReplyOut:
        """Answer one query, persisting the turn into the user's transcript.

        Every engine call is best-effort: a missing scan, an unseeded catalog, or
        any unexpected error degrades to a helpful reply rather than a 500.
        """
        lang = lang if lang in ASSISTANT_LANGS else detect_lang(query)
        conv = ConversationService(self.db)
        history = await conv.list(user.id)
        ctx = AssistantContext(
            user=user,
            query=query,
            lang=lang,
            history=history,
            now=datetime.now(UTC),
        )
        reply = await self._answer_safely(ctx)

        # Persist the turn (M3.1 conversation memory) so follow-ups keep context
        # and a page reload can restore the chat.
        await conv.append(user.id, "user", query)
        await conv.append(user.id, "assistant", reply.message, intent=reply.intent, lang=reply.lang)
        await self.db.commit()
        return reply

    async def conversation(self, user: User) -> ConversationOut:
        """The user's recent transcript, oldest first (for history restore)."""
        items = await ConversationService(self.db).list(user.id)
        return ConversationOut(items=items)

    async def clear_conversation(self, user: User) -> None:
        """Drop the user's entire transcript (clear-chat)."""
        await ConversationService(self.db).clear(user.id)
        await self.db.commit()

    async def _answer_safely(self, ctx: AssistantContext) -> AssistantReplyOut:
        """Run the active provider; degrade to the local engine on any failure."""
        try:
            return await self._provider.answer(ctx)
        except Exception:
            logger.warning("assistant_provider_failed", exc_info=True)
            return await LocalConversationProvider(self.db).answer(ctx)
