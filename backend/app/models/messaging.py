"""Marketplace buyer↔seller messaging models (M4, Task 5).

Two tables power secure inquiry/chat threads between a marketplace participant
(the **buyer** who starts the conversation) and a seller (the shop owner, or
the farmer behind a crop listing):

* :class:`MarketplaceConversation` — one thread. Owned by the two
  participants (``buyer_id`` / ``seller_id`` → ``users.id``). It optionally
  references the listing or product that sparked the enquiry, carries a
  lifecycle ``status`` (``active`` | ``closed``) and remembers ``last_message_at``
  so the inbox sorts by recency without joining messages.
* :class:`MarketplaceMessage` — one turn in a thread: ``sender_id``, text
  ``content`` and ``read_at`` (NULL until the counterpart opens the thread).

The table names are prefixed ``marketplace_`` deliberately — the M3.1
assistant already owns ``conversation_messages`` (a per-user AI transcript with
a completely different shape), and these are distinct concepts that must never
collide. No sensitive data is stored beyond the message text itself; ownership
and participant checks live in ``app.services.messaging``.
"""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base
from app.models.base import TimestampMixin

# Conversation lifecycle (app-level validation).
STATUS_ACTIVE = "active"
STATUS_CLOSED = "closed"
CONVERSATION_STATUSES = (STATUS_ACTIVE, STATUS_CLOSED)


class MarketplaceConversation(Base, TimestampMixin):
    __tablename__ = "marketplace_conversations"
    __table_args__ = (
        # The inbox filters by status; the buyer/seller columns carry their own
        # ``index=True`` indexes (one per side of the thread).
        Index("ix_marketplace_conversations_status", "status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    # The participant who started the thread (any authenticated user).
    buyer_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    # The participant on the selling side — a shop seller for products, the
    # listing farmer for crops (both are ``users.id`` rows).
    seller_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    # Optional context that sparked the enquiry (exactly one of the two when
    # present). SET NULL so a deleted listing/product never orphans the thread.
    listing_id: Mapped[int | None] = mapped_column(
        ForeignKey("crop_listings.id", ondelete="SET NULL"), nullable=True
    )
    product_id: Mapped[int | None] = mapped_column(
        ForeignKey("products.id", ondelete="SET NULL"), nullable=True
    )
    # active | closed (app-level validation; closed threads reject new messages).
    status: Mapped[str] = mapped_column(
        String(20), default=STATUS_ACTIVE, server_default=text("'active'"), nullable=False
    )
    last_message_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class MarketplaceMessage(Base, TimestampMixin):
    __tablename__ = "marketplace_messages"
    __table_args__ = (
        # The thread is fetched oldest-first; the inbox preview takes the newest
        # per conversation — a composite index covers both scans.
        Index(
            "ix_marketplace_messages_conversation_created",
            "conversation_id",
            "created_at",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    conversation_id: Mapped[int] = mapped_column(
        ForeignKey("marketplace_conversations.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    sender_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    # NULL until the counterpart opens the thread (mark-read flow).
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
