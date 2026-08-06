"""AI assistant schemas (M3 Task 6 → M3.1 conversational upgrade).

The assistant is a provider-backed conversational layer over the *existing*
engines (treatment, soil, recovery, calendar, scans) — it never re-implements
policy. The client sends a free-text query plus a language code; the service
answers with a structured reply: ``message`` is the conversational bubble
(localized to the chosen language) and ``sections`` are speakable sub-blocks
the frontend can render as cards and/or feed to text-to-speech.

M3.1 adds conversation memory: ``ConversationMessageOut`` / ``ConversationOut``
back the ``GET/DELETE /assistant/conversation`` endpoints so a page reload
restores the chat and the engine can answer follow-ups with context.

Languages the assistant can answer in today mirror the shipped i18n registry
(``en``, ``hi``). M4 adds more Indian languages by extending the provider's
template tables — this schema does not change.
"""

from datetime import datetime

from pydantic import BaseModel, Field

# Reply languages. ``lang`` is optional on the request: when omitted the
# service auto-detects it from the query's script (Devanagari → Hindi).
ASSISTANT_LANGS = ("en", "hi")

# Canonical intents the router can return (M3.1: extended for conversational
# behavior — social intents, statement acknowledgments, a non-agriculture
# boundary, and the LLM-provider "conversation" intent).
ASSISTANT_INTENTS = (
    # Social / static
    "greeting",
    "identity",
    "help",
    "thanks",
    "smalltalk",
    # Data-backed (reuse the engine services)
    "disease",
    "disease_explain",
    "symptoms",
    "treatment",
    "fertilizer",
    "watering",
    "neem",
    "soil",
    "recovery",
    "recovery_timeline",
    "calendar",
    # Conversational plumbing
    "report",  # a statement the assistant acknowledges ("my tomato has blight")
    "conversation",  # LLM-provider free-form answer
    # Boundary
    "non_agriculture",
)


class AssistantIn(BaseModel):
    """POST /assistant — one user query."""

    query: str = Field(
        min_length=1,
        max_length=500,
        description="Free-text question (English or Hindi)",
    )
    lang: str | None = Field(
        default=None,
        description="Reply language; auto-detected from the query when omitted",
    )


class AssistantSection(BaseModel):
    """One speakable / renderable sub-block of the reply."""

    title: str = Field(description="Section heading (localized)")
    body: str = Field(
        description="Plain-text content (localized chrome; catalog content stays English)"
    )


class AssistantReplyOut(BaseModel):
    """The structured conversational reply for one query."""

    intent: str = Field(description="One of the canonical ASSISTANT_INTENTS")
    message: str = Field(description="The conversational bubble text (localized)")
    sections: list[AssistantSection] = Field(default_factory=list)
    lang: str = Field(description="Language the reply is written in")


class ConversationMessageOut(BaseModel):
    """One persisted turn of the user's chat (for history restore)."""

    id: int
    role: str = Field(description="'user' | 'assistant'")
    content: str = Field(description="The message text")
    intent: str | None = Field(default=None, description="Assistant-turn intent")
    lang: str | None = Field(default=None, description="Assistant-turn language")
    created_at: datetime = Field(description="Server-side turn timestamp")


class ConversationOut(BaseModel):
    """The user's recent transcript, oldest first."""

    items: list[ConversationMessageOut]
