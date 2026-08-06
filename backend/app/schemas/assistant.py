"""Voice AI assistant schemas (M3, Task 6).

The assistant is a rule-based conversational layer over the *existing* engines
(treatment, soil, recovery, calendar, scans) — it never re-implements policy.
The client sends a free-text query plus a language code; the service answers
with a structured reply: ``message`` is the conversational bubble (localized to
the chosen language) and ``sections`` are speakable sub-blocks the frontend can
render as cards and/or feed to text-to-speech.

Languages the assistant can answer in today mirror the shipped i18n registry
(``en``, ``hi``). M4 adds more Indian languages by extending the service's
keyword + template tables — this schema does not change.
"""

from pydantic import BaseModel, Field

# Reply languages. ``lang`` is optional on the request: when omitted the
# service auto-detects it from the query's script (Devanagari → Hindi).
ASSISTANT_LANGS = ("en", "hi")

# Canonical intents the router can return.
ASSISTANT_INTENTS = (
    "greeting",
    "help",
    "disease",
    "treatment",
    "fertilizer",
    "soil",
    "calendar",
    "recovery",
    "fallback",
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
