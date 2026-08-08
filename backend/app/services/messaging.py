"""Marketplace buyer↔seller messaging service (M4, Task 5).

One service owns every messaging rule so the router only maps HTTP semantics.
Two participants drive it:

* **Buyers** (any authenticated user) start a thread from a crop listing, a
  product, or a shop, send messages, and mark the thread read.
* **Sellers** (the listing farmer or the shop owner) reply from the same
  thread and close it when the enquiry is done.

Security follows the platform's ownership convention: a conversation you are
not part of (and any missing id) answers ``404`` so ids can't be enumerated or
manipulated — the same guard scans/recovery/calendar use. Only participants can
read, message, mark-read or close a thread. Duplicate threads for the same
buyer + seller + listing/product are *reused* (a closed one is reopened), so a
second "Contact Seller" click never stacks a new conversation.

No WebSocket layer exists yet by design (M4 Task 5 is API-based); the methods
are shaped so a real-time adapter can ride on top later without changing the
read/write surface.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.marketplace import CropListing, Product
from app.models.messaging import (
    STATUS_ACTIVE,
    STATUS_CLOSED,
    MarketplaceConversation,
    MarketplaceMessage,
)
from app.models.user import SellerProfile, User
from app.schemas.messaging import (
    LAST_MESSAGE_PREVIEW_LENGTH,
    ConversationCreate,
    ConversationDetailOut,
    ConversationListItemOut,
    ListingRefOut,
    MessageIn,
    MessageOut,
    ParticipantOut,
    ProductRefOut,
    ReadResultOut,
)

logger = get_logger(__name__)


class ConversationNotFoundError(Exception):
    """No conversation with this id — or one the caller isn't a participant of."""


class ConversationClosedError(Exception):
    """The thread is closed; new messages are rejected."""


class ConversationValidationError(Exception):
    """Bad create context (self-contact, wrong/missing listing/product/seller)."""


class MessagingService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ── Lifecycle ─────────────────────────────────────────────────────────

    async def create_conversation(
        self, user: User, payload: ConversationCreate
    ) -> ConversationDetailOut:
        """Start (or reuse) a thread. Exactly one context — ``seller_id`` /
        ``listing_id`` / ``product_id`` — must be provided; ``message`` is an
        optional opening turn. A matching existing thread is returned instead
        of a duplicate; a closed match is reopened with its history intact."""
        seller_id = await self._resolve_seller(payload)
        if seller_id == user.id:
            raise ConversationValidationError("you cannot start a conversation with yourself")

        conversation = await self._find_reusable(
            user.id, seller_id, payload.listing_id, payload.product_id
        )
        if conversation is None:
            conversation = MarketplaceConversation(
                buyer_id=user.id,
                seller_id=seller_id,
                listing_id=payload.listing_id,
                product_id=payload.product_id,
                status=STATUS_ACTIVE,
            )
            self.db.add(conversation)
            await self.db.flush()
        elif conversation.status != STATUS_ACTIVE:
            # Reopening a previously-closed thread for the same item keeps the
            # history and still prevents duplicate conversations.
            conversation.status = STATUS_ACTIVE
            conversation.updated_at = datetime.now(UTC)
            self.db.add(conversation)
            await self.db.flush()

        if payload.message:
            await self._append_message(user, conversation, payload.message)
        await self.db.commit()
        logger.info(
            "conversation_created",
            conversation_id=conversation.id,
            buyer_id=user.id,
            seller_id=seller_id,
        )
        return await self.detail(user, conversation.id)

    async def list_conversations(self, user: User) -> list[ConversationListItemOut]:
        """Every thread the user is a participant of (buyer or seller), newest
        activity first. Each row carries the viewer-relative unread count and a
        last-message preview so the inbox needs no per-thread round-trips."""
        rows = await self.db.scalars(
            select(MarketplaceConversation)
            .where(
                or_(
                    MarketplaceConversation.buyer_id == user.id,
                    MarketplaceConversation.seller_id == user.id,
                )
            )
            .order_by(
                MarketplaceConversation.last_message_at.desc().nulls_last(),
                MarketplaceConversation.created_at.desc(),
                MarketplaceConversation.id.desc(),
            )
        )
        conversations = rows.all()
        conversation_ids = [c.id for c in conversations]
        unread = await self._unread_counts(user.id, conversation_ids)
        latest = await self._latest_messages(conversation_ids)
        return [
            await self._build_item(user, conversation, unread, latest)
            for conversation in conversations
        ]

    async def detail(self, user: User, conversation_id: int) -> ConversationDetailOut:
        """One thread, oldest-first, with both participants, the related
        listing/product and the viewer-relative unread count."""
        conversation = await self._conversation_for_participant(conversation_id, user.id)
        unread = await self._unread_counts(user.id, [conversation.id])
        return ConversationDetailOut(
            id=conversation.id,
            status=conversation.status,
            created_at=conversation.created_at,
            updated_at=conversation.updated_at,
            last_message_at=conversation.last_message_at,
            unread_count=unread.get(conversation.id, 0),
            buyer=await self._participant(conversation.buyer_id),
            seller=await self._participant(conversation.seller_id),
            listing=await self._listing_ref(conversation.listing_id),
            product=await self._product_ref(conversation.product_id),
            messages=await self._messages(conversation.id),
        )

    async def send_message(
        self, user: User, conversation_id: int, payload: MessageIn
    ) -> MessageOut:
        """Append one turn. Rejected (``409``) once the thread is closed."""
        conversation = await self._conversation_for_participant(conversation_id, user.id)
        if conversation.status != STATUS_ACTIVE:
            raise ConversationClosedError(
                "this conversation is closed; no new messages can be sent"
            )
        message = await self._append_message(user, conversation, payload.content)
        await self.db.commit()
        await self.db.refresh(message)
        logger.info("message_sent", conversation_id=conversation.id, sender_id=user.id)
        return MessageOut(
            id=message.id,
            conversation_id=message.conversation_id,
            sender_id=message.sender_id,
            sender_name=user.name,
            content=message.content,
            created_at=message.created_at,
            read_at=message.read_at,
        )

    async def mark_read(self, user: User, conversation_id: int) -> ReadResultOut:
        """Mark every message from the other side as read; leaves the viewer's
        own messages untouched."""
        conversation = await self._conversation_for_participant(conversation_id, user.id)
        now = datetime.now(UTC)
        rows = await self.db.scalars(
            select(MarketplaceMessage).where(
                MarketplaceMessage.conversation_id == conversation.id,
                MarketplaceMessage.sender_id != user.id,
                MarketplaceMessage.read_at.is_(None),
            )
        )
        for message in rows.all():
            message.read_at = now
        await self.db.commit()
        return ReadResultOut(conversation_id=conversation.id, unread_count=0)

    async def close(self, user: User, conversation_id: int) -> ConversationListItemOut:
        """Close a thread (idempotent — closing a closed thread is a no-op).
        History stays visible; new messages are rejected from now on."""
        conversation = await self._conversation_for_participant(conversation_id, user.id)
        if conversation.status == STATUS_ACTIVE:
            conversation.status = STATUS_CLOSED
            conversation.updated_at = datetime.now(UTC)
            self.db.add(conversation)
            await self.db.commit()
            logger.info("conversation_closed", conversation_id=conversation.id, user_id=user.id)
        unread = await self._unread_counts(user.id, [conversation.id])
        latest = await self._latest_messages([conversation.id])
        return await self._build_item(user, conversation, unread, latest)

    # ── Internals ────────────────────────────────────────────────────────

    async def _resolve_seller(self, payload: ConversationCreate) -> int:
        """Derive the selling participant from the create context. ``listing_id``
        resolves to its farmer, ``product_id`` to its shop seller; an explicit
        ``seller_id`` is accepted for context-free enquiries. Exactly one of the
        three must be present."""
        contexts = [
            payload.seller_id is not None,
            payload.listing_id is not None,
            payload.product_id is not None,
        ]
        if contexts.count(True) != 1:
            raise ConversationValidationError(
                "provide exactly one of seller_id, listing_id, product_id"
            )
        if payload.seller_id is not None:
            seller = await self.db.get(User, payload.seller_id)
            if seller is None or seller.status != "active":
                raise ConversationValidationError("seller not found")
            return seller.id
        if payload.listing_id is not None:
            listing = await self.db.get(CropListing, payload.listing_id)
            if listing is None:
                raise ConversationValidationError("listing not found")
            return listing.farmer_id
        product = await self.db.get(Product, payload.product_id)
        if product is None:
            raise ConversationValidationError("product not found")
        return product.seller_id

    async def _find_reusable(
        self,
        buyer_id: int,
        seller_id: int,
        listing_id: int | None,
        product_id: int | None,
    ) -> MarketplaceConversation | None:
        """A matching thread for the same buyer + seller + listing/product, if
        one exists. ``is_(None)`` keeps the null-safe semantics so a context-free
        thread (no listing/product) still matches only its own kind. Active
        threads are preferred so reopening only kicks in when nothing active
        remains."""
        return await self.db.scalar(
            select(MarketplaceConversation)
            .where(
                MarketplaceConversation.buyer_id == buyer_id,
                MarketplaceConversation.seller_id == seller_id,
                MarketplaceConversation.listing_id.is_(listing_id),
                MarketplaceConversation.product_id.is_(product_id),
            )
            .order_by(
                MarketplaceConversation.status.asc(),
                MarketplaceConversation.updated_at.desc(),
                MarketplaceConversation.id.desc(),
            )
            .limit(1)
        )

    async def _conversation_for_participant(
        self, conversation_id: int, user_id: int
    ) -> MarketplaceConversation:
        """Fetch a conversation the caller actually belongs to. Anything else —
        missing id or another user's thread — answers ``404`` (enumeration
        guard, matching scans/recovery/calendar)."""
        conversation = await self.db.get(MarketplaceConversation, conversation_id)
        if conversation is None or (
            conversation.buyer_id != user_id and conversation.seller_id != user_id
        ):
            raise ConversationNotFoundError(f"conversation {conversation_id} not found")
        return conversation

    async def _append_message(
        self, user: User, conversation: MarketplaceConversation, content: str
    ) -> MarketplaceMessage:
        """Insert a message and touch the thread's recency stamps."""
        now = datetime.now(UTC)
        message = MarketplaceMessage(
            conversation_id=conversation.id,
            sender_id=user.id,
            content=content,
            read_at=None,
        )
        conversation.last_message_at = now
        conversation.updated_at = now
        self.db.add(message)
        await self.db.flush()
        return message

    async def _unread_counts(self, user_id: int, conversation_ids: list[int]) -> dict[int, int]:
        """Messages from the other side that the viewer hasn't read yet."""
        if not conversation_ids:
            return {}
        rows = await self.db.execute(
            select(
                MarketplaceMessage.conversation_id,
                func.count(MarketplaceMessage.id),
            )
            .where(
                MarketplaceMessage.conversation_id.in_(conversation_ids),
                MarketplaceMessage.sender_id != user_id,
                MarketplaceMessage.read_at.is_(None),
            )
            .group_by(MarketplaceMessage.conversation_id)
        )
        return {conversation_id: count for conversation_id, count in rows.all()}

    async def _latest_messages(self, conversation_ids: list[int]) -> dict[int, MarketplaceMessage]:
        """Newest message per conversation (one query, ordered per thread)."""
        if not conversation_ids:
            return {}
        rows = await self.db.scalars(
            select(MarketplaceMessage)
            .where(MarketplaceMessage.conversation_id.in_(conversation_ids))
            .order_by(
                MarketplaceMessage.conversation_id.asc(),
                MarketplaceMessage.created_at.desc(),
                MarketplaceMessage.id.desc(),
            )
        )
        latest: dict[int, MarketplaceMessage] = {}
        for row in rows:
            if row.conversation_id not in latest:
                latest[row.conversation_id] = row
        return latest

    async def _messages(self, conversation_id: int) -> list[MessageOut]:
        """The full thread, oldest-first, with sender names attached."""
        rows = await self.db.scalars(
            select(MarketplaceMessage)
            .where(MarketplaceMessage.conversation_id == conversation_id)
            .order_by(
                MarketplaceMessage.created_at.asc(),
                MarketplaceMessage.id.asc(),
            )
        )
        messages = rows.all()
        names = await self._user_names({m.sender_id for m in messages})
        return [
            MessageOut(
                id=message.id,
                conversation_id=message.conversation_id,
                sender_id=message.sender_id,
                sender_name=names.get(message.sender_id, ""),
                content=message.content,
                created_at=message.created_at,
                read_at=message.read_at,
            )
            for message in messages
        ]

    async def _user_names(self, user_ids: set[int]) -> dict[int, str]:
        if not user_ids:
            return {}
        rows = await self.db.scalars(select(User).where(User.id.in_(user_ids)))
        return {user.id: user.name for user in rows.all()}

    async def _build_item(
        self,
        user: User,
        conversation: MarketplaceConversation,
        unread: dict[int, int],
        latest: dict[int, MarketplaceMessage],
    ) -> ConversationListItemOut:
        last = latest.get(conversation.id)
        return ConversationListItemOut(
            id=conversation.id,
            status=conversation.status,
            created_at=conversation.created_at,
            updated_at=conversation.updated_at,
            last_message_at=conversation.last_message_at,
            last_message_preview=_preview(last.content) if last is not None else None,
            last_message_sender_id=last.sender_id if last is not None else None,
            unread_count=unread.get(conversation.id, 0),
            buyer=await self._participant(conversation.buyer_id),
            seller=await self._participant(conversation.seller_id),
            listing=await self._listing_ref(conversation.listing_id),
            product=await self._product_ref(conversation.product_id),
        )

    async def _participant(self, user_id: int) -> ParticipantOut:
        """Compact marketplace-visible identity for one side of a thread."""
        user = await self.db.get(User, user_id)
        if user is None:
            return ParticipantOut(id=user_id, name="", role="", shop_name=None, avatar_url=None)
        profile = await self.db.scalar(
            select(SellerProfile).where(SellerProfile.user_id == user_id)
        )
        return ParticipantOut(
            id=user.id,
            name=user.name,
            role=user.role,
            shop_name=profile.shop_name if profile is not None else None,
            avatar_url=user.avatar_url,
        )

    async def _listing_ref(self, listing_id: int | None) -> ListingRefOut | None:
        if listing_id is None:
            return None
        listing = await self.db.get(CropListing, listing_id)
        if listing is None:
            return None
        image = listing.images[0] if listing.images else None
        return ListingRefOut(id=listing.id, crop_name=listing.crop_name, image=image)

    async def _product_ref(self, product_id: int | None) -> ProductRefOut | None:
        if product_id is None:
            return None
        product = await self.db.get(Product, product_id)
        if product is None:
            return None
        image = product.images[0] if product.images else None
        return ProductRefOut(id=product.id, name=product.name, image=image)


def _preview(content: str) -> str:
    """Collapse whitespace and truncate to the inbox preview length."""
    text = " ".join(content.split())
    if len(text) > LAST_MESSAGE_PREVIEW_LENGTH:
        return f"{text[: LAST_MESSAGE_PREVIEW_LENGTH - 1]}…"
    return text
