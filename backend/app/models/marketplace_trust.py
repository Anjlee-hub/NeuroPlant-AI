"""Marketplace trust models (M4, Task 6) — favourites and reviews.

Two tables power the trust layer that sits on top of the existing marketplace:

* :class:`MarketplaceFavorite` — one saved item (a crop listing *or* a product)
  per user. Backed by unique constraints per target kind so adding the same
  listing twice is impossible; the service treats ``add`` as idempotent and
  returns the existing row. Exactly one target context is required (enforced by
  the service and by a DB CHECK).
* :class:`MarketplaceReview` — one 1–5 rating + optional title + review text by
  a buyer against an item. ``seller_id`` is the *subject* of the review (the
  listing's farmer or the product's shop owner), stored denormalised so a
  seller's reputation aggregates across every listing and product in one query
  without joins. One review per reviewer per target is enforced with unique
  constraints; editing and deleting are owner-scoped in the service.

FK semantics deliberately differ between the two tables:

* **Favourites** use ``CASCADE`` on the item reference — when a listing or
  product is deleted the saved copy dies with it (a favourite of a deleted item
  is meaningless).
* **Reviews** use ``SET NULL`` — review *history* (and the seller reputation it
  feeds) survives the item being retired; the review keeps its ``seller_id`` and
  renders without a target link. There is deliberately **no** exactly-one CHECK
  on reviews: on a SET NULL the row would legitimately hold two NULLs, and a
  CHECK would abort the parent delete on Postgres.

Both tables are prefixed ``marketplace_`` (the M3.1 assistant already owns
``conversation_messages`` and must never collide). No anonymous reviews exist:
``reviewer_id`` is always the authenticated user, enforced in the service.
"""

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base
from app.models.base import TimestampMixin

# 1–5 star scale (app-validated in the schema as well).
RATING_MIN = 1
RATING_MAX = 5

# Review text bounds (mirrors the schema's boundary validation).
REVIEW_TITLE_MAX_LENGTH = 200
REVIEW_CONTENT_MAX_LENGTH = 2000

_EXACTLY_ONE_FAVOURITE_TARGET = (
    "(listing_id IS NOT NULL AND product_id IS NULL)"
    " OR (listing_id IS NULL AND product_id IS NOT NULL)"
)


class MarketplaceFavorite(Base, TimestampMixin):
    __tablename__ = "marketplace_favorites"
    __table_args__ = (
        # A saved item is a listing OR a product, never both and never neither.
        CheckConstraint(
            _EXACTLY_ONE_FAVOURITE_TARGET,
            name="ck_marketplace_favorites_one_target",
        ),
        # Idempotence: one saved copy per user per item. Two unique constraints
        # (one per target kind) work under SQLite's "NULLs are distinct" unique
        # semantics because exactly one target column is ever non-NULL.
        UniqueConstraint("user_id", "listing_id", name="uq_marketplace_favorites_listing"),
        UniqueConstraint("user_id", "product_id", name="uq_marketplace_favorites_product"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    # CASCADE so a saved copy never dangles after the item is deleted.
    listing_id: Mapped[int | None] = mapped_column(
        ForeignKey("crop_listings.id", ondelete="CASCADE"), nullable=True
    )
    product_id: Mapped[int | None] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"), nullable=True
    )


class MarketplaceReview(Base, TimestampMixin):
    __tablename__ = "marketplace_reviews"
    __table_args__ = (
        # One review per reviewer per target — same NULL-safe unique trick as
        # favourites (exactly one target column is ever non-NULL).
        UniqueConstraint("reviewer_id", "listing_id", name="uq_marketplace_reviews_listing"),
        UniqueConstraint("reviewer_id", "product_id", name="uq_marketplace_reviews_product"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    # The reviewer (any authenticated user — never anonymous).
    reviewer_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    # The review's subject: the listing's farmer or the product's shop owner.
    # Denormalised so seller reputation aggregates in one query.
    seller_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    # SET NULL so review history survives the item being deleted.
    listing_id: Mapped[int | None] = mapped_column(
        ForeignKey("crop_listings.id", ondelete="SET NULL"), nullable=True
    )
    product_id: Mapped[int | None] = mapped_column(
        ForeignKey("products.id", ondelete="SET NULL"), nullable=True
    )
    # 1–5 star rating (app-validated); optional short title; required review text.
    rating: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str | None] = mapped_column(String(REVIEW_TITLE_MAX_LENGTH), nullable=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
