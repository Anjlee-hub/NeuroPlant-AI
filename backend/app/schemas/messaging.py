"""Marketplace messaging schemas (M4, Task 5).

Request/response DTOs for the buyer↔seller inquiry system. The create payload
takes exactly one context (``seller_id`` / ``listing_id`` / ``product_id``) —
that rule is enforced in the service (a business rule, like the ownership
guards), while message length is bounded here at the boundary.

``ConversationListItemOut`` is the inbox row (unread count + last-message
preview, both viewer-relative); ``ConversationDetailOut`` is the full thread.
No participant exposes anything beyond what the marketplace already shows
(name / role / shop name) — never phone, address or other account data.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

# One message may not exceed this many characters (server-side length limit).
MESSAGE_MAX_LENGTH = 2000
# Inbox previews are truncated so one long message doesn't bloat the list.
LAST_MESSAGE_PREVIEW_LENGTH = 120

CONVERSATION_STATUS_PATTERN = "^(active|closed)$"


def _strip_non_blank(value: str) -> str:
    """Trim padding and reject a message that is only whitespace.

    ``min_length`` counts raw characters, so a payload of spaces passes it; the
    blank-content guard is this validator's job. The trimmed value is what gets
    persisted.
    """
    stripped = value.strip()
    if not stripped:
        raise ValueError("content must not be blank")
    return stripped


# ── Requests ──────────────────────────────────────────────────────────────


class ConversationCreate(BaseModel):
    """POST /marketplace/conversations — start (or reuse) a thread.

    Exactly one of ``seller_id`` / ``listing_id`` / ``product_id`` must be
    provided (enforced in the service). ``listing_id`` resolves the seller to
    the listing's farmer; ``product_id`` to the product's shop seller; an
    explicit ``seller_id`` allows a context-free enquiry. ``message`` is an
    optional opening message.
    """

    seller_id: int | None = Field(default=None, gt=0)
    listing_id: int | None = Field(default=None, gt=0)
    product_id: int | None = Field(default=None, gt=0)
    message: str | None = Field(default=None, min_length=1, max_length=MESSAGE_MAX_LENGTH)

    @field_validator("message")
    @classmethod
    def _opening_message(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return _strip_non_blank(value)


class MessageIn(BaseModel):
    """POST /marketplace/conversations/{id}/messages — one turn."""

    content: str = Field(min_length=1, max_length=MESSAGE_MAX_LENGTH)

    @field_validator("content")
    @classmethod
    def _content(cls, value: str) -> str:
        return _strip_non_blank(value)


# ── Payloads ──────────────────────────────────────────────────────────────


class ParticipantOut(BaseModel):
    """Compact identity of one side of a thread.

    Only marketplace-visible fields are exposed (name / role / shop name /
    avatar) — never contact or account data.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    role: str
    shop_name: str | None = None
    avatar_url: str | None = None


class ListingRefOut(BaseModel):
    """The crop listing a conversation is about (when it has one)."""

    id: int
    crop_name: str
    image: str | None = None


class ProductRefOut(BaseModel):
    """The product a conversation is about (when it has one)."""

    id: int
    name: str
    image: str | None = None


class MessageOut(BaseModel):
    """One message as returned by the API."""

    id: int
    conversation_id: int
    sender_id: int
    sender_name: str
    content: str
    created_at: datetime
    read_at: datetime | None


class ConversationListItemOut(BaseModel):
    """One inbox row — viewer-relative unread count and last-message preview."""

    id: int
    status: str
    created_at: datetime
    updated_at: datetime
    last_message_at: datetime | None
    last_message_preview: str | None
    last_message_sender_id: int | None
    unread_count: int = Field(ge=0)
    buyer: ParticipantOut
    seller: ParticipantOut
    listing: ListingRefOut | None
    product: ProductRefOut | None


class ConversationDetailOut(BaseModel):
    """GET /marketplace/conversations/{id} — the full thread."""

    id: int
    status: str
    created_at: datetime
    updated_at: datetime
    last_message_at: datetime | None
    unread_count: int = Field(ge=0)
    buyer: ParticipantOut
    seller: ParticipantOut
    listing: ListingRefOut | None
    product: ProductRefOut | None
    messages: list[MessageOut] = Field(default_factory=list)


class ReadResultOut(BaseModel):
    """Response of the mark-as-read endpoint — the viewer's remaining unread."""

    conversation_id: int
    unread_count: int = Field(ge=0)
