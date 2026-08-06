"""AI assistant conversation memory (M3.1).

A rolling per-user transcript that gives the assistant context for follow-up
questions across requests (stateless HTTP → stateful chat). One row per turn:
the farmer's question and the assistant's reply are both persisted so a page
reload can restore the chat and the conversational engine can resolve
anaphora ("How do I treat *it*?") against earlier mentions.

``role`` is ``user`` or ``assistant``; ``intent`` and ``lang`` are recorded on
assistant turns so the UI can restore badges and voice locale. The transcript
is capped by :class:`ConversationService` (oldest turns are trimmed) — the
model itself imposes no size limit.
"""

from __future__ import annotations

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base
from app.models.base import TimestampMixin


class ConversationMessage(Base, TimestampMixin):
    __tablename__ = "conversation_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )

    # "user" | "assistant" — the turn's speaker.
    role: Mapped[str] = mapped_column(String(16), nullable=False)

    # The full message text (question or localized reply bubble).
    content: Mapped[str] = mapped_column(Text, nullable=False)

    # Assistant-turn metadata: canonical intent + reply language.
    intent: Mapped[str | None] = mapped_column(String(40), nullable=True)
    lang: Mapped[str | None] = mapped_column(String(8), nullable=True)
