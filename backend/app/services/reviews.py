"""Marketplace reviews & reputation service (M4, Task 6).

One service owns every review rule so the router only maps HTTP semantics.

* Any authenticated user reviews a crop listing or a product (exactly one
  target, ``400`` otherwise). The review's ``seller_id`` is derived from the
  target — the listing's farmer or the product's shop owner — so a seller's
  reputation aggregates across every listing and product in one query.
* **Dedup** — one review per reviewer per target; a second attempt answers
  ``409`` (unique constraints back it up at the database level).
* **Self-review** is rejected with ``400`` (a farmer cannot rate their own
  listing).
* **Ownership** — editing or deleting a review that isn't the caller's (and
  any missing id) answers ``404`` (enumeration guard).
* **Reputation** — :meth:`rating_summary` returns average / total / star
  distribution for a seller; the marketplace service calls it when assembling
  ``SellerOut`` / ``ShopSummaryOut`` / ``FarmerSummaryOut`` so every surface
  shows live, review-driven ratings (the old stored placeholder is never read).

The list endpoint is the read model: one call for a target/seller returns the
reviews, the aggregate summary, and (for a single item) the caller's own review
so the UI knows whether to show "Write a review" or "Edit your review".

M5 Task 3: integration with NotificationTriggerService for review_received
notifications.
"""

from __future__ import annotations

from math import ceil

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.marketplace import CropListing, Product
from app.models.marketplace_trust import (
    RATING_MAX,
    RATING_MIN,
    MarketplaceReview,
)
from app.models.user import User
from app.schemas.messaging import ListingRefOut, ProductRefOut
from app.schemas.reviews import (
    RatingSummaryOut,
    ReviewCreate,
    ReviewOut,
    ReviewPageOut,
    ReviewUpdate,
)
from app.services.notification_triggers import NotificationTriggerService

logger = get_logger(__name__)

# Pagination — same defaults as the rest of the marketplace (kept local so this
# module never imports the marketplace *service* and creates a cycle).
DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100


class ReviewValidationError(Exception):
    """Bad review (both/none/unknown target, or reviewing your own item)."""


class ReviewDuplicateError(Exception):
    """The caller has already reviewed this exact target."""


class ReviewNotFoundError(Exception):
    """No review with this id — or one that isn't the caller's."""


class ReviewsService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ── CRUD ─────────────────────────────────────────────────────────────

    async def create(self, user: User, payload: ReviewCreate) -> ReviewOut:
        """Post one review of a listing or product (the reviewer is always the
        authenticated user — never anonymous)."""
        listing, product, seller_id = await self._resolve_target(
            payload.listing_id, payload.product_id
        )
        if seller_id == user.id:
            raise ReviewValidationError("you cannot review your own item")
        existing = await self._find_by_target(user.id, payload.listing_id, payload.product_id)
        if existing is not None:
            raise ReviewDuplicateError(
                "you have already reviewed this item; edit your existing review"
            )
        review = MarketplaceReview(
            reviewer_id=user.id,
            seller_id=seller_id,
            listing_id=payload.listing_id,
            product_id=payload.product_id,
            rating=payload.rating,
            title=payload.title,
            content=payload.content,
        )
        self.db.add(review)
        await self.db.commit()
        await self.db.refresh(review)
        logger.info(
            "review_created",
            review_id=review.id,
            reviewer_id=user.id,
            seller_id=seller_id,
            rating=review.rating,
        )

        # M5 Task 3: notify the reviewed seller
        triggers = NotificationTriggerService(self.db)
        await triggers.notify_review_received(
            seller_id=seller_id,
            review_id=review.id,
            listing_id=payload.listing_id,
            product_id=payload.product_id,
            rating=payload.rating,
            reviewer_name=user.name,
        )

        return await self._build(review)

    async def update(self, user: User, review_id: int, payload: ReviewUpdate) -> ReviewOut:
        """Edit one of the caller's own reviews (only sent fields change)."""
        review = await self._for_owner(review_id, user.id)
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(review, field, value)
        self.db.add(review)
        await self.db.commit()
        await self.db.refresh(review)
        logger.info("review_updated", review_id=review.id, reviewer_id=user.id)
        return await self._build(review)

    async def delete(self, user: User, review_id: int) -> None:
        """Remove one of the caller's own reviews (404 for others')."""
        review = await self._for_owner(review_id, user.id)
        await self.db.delete(review)
        await self.db.commit()
        logger.info("review_deleted", review_id=review_id, reviewer_id=user.id)

    # ── Reads ─────────────────────────────────────────────────────────────

    async def list_reviews(
        self,
        user: User,
        *,
        listing_id: int | None = None,
        product_id: int | None = None,
        seller_id: int | None = None,
        page: int = 1,
        page_size: int = DEFAULT_PAGE_SIZE,
    ) -> ReviewPageOut:
        """Paginated reviews for one target (listing/product) or one seller,
        newest first. ``summary`` aggregates over the same subject scope, and
        ``my_review`` is populated when a single item is filtered."""
        subject = self._subject_scope(listing_id, product_id, seller_id)
        conds = self._where_for_scope(subject)
        page = max(1, page)
        page_size = max(1, min(page_size, MAX_PAGE_SIZE))

        count_stmt = select(func.count(MarketplaceReview.id)).where(*conds)
        total = int(await self.db.scalar(count_stmt) or 0)
        rows = await self.db.scalars(
            select(MarketplaceReview)
            .where(*conds)
            .order_by(MarketplaceReview.created_at.desc(), MarketplaceReview.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        reviews = rows.all()
        names = await self._reviewer_names({review.reviewer_id for review in reviews})
        items = [await self._build(review, names=names) for review in reviews]
        summary = await self._summary_for_scope(subject)
        my_review = None
        if listing_id is not None or product_id is not None:
            mine = await self._find_by_target(user.id, listing_id, product_id)
            if mine is not None:
                my_review = await self._build(mine)
        return ReviewPageOut(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            pages=ceil(total / page_size) if total else 0,
            summary=summary,
            my_review=my_review,
        )

    async def mine(self, user: User) -> list[ReviewOut]:
        """Every review the caller wrote, newest first (edit/delete surface)."""
        rows = await self.db.scalars(
            select(MarketplaceReview)
            .where(MarketplaceReview.reviewer_id == user.id)
            .order_by(MarketplaceReview.created_at.desc(), MarketplaceReview.id.desc())
        )
        return [await self._build(review) for review in rows.all()]

    async def rating_summary(self, seller_id: int) -> RatingSummaryOut:
        """A seller's reputation: average, count and 5→1 distribution across
        every review of that seller (regardless of which listing/product)."""
        return await self._summary_for_scope(("seller", seller_id))

    # ── Internals ────────────────────────────────────────────────────────

    @staticmethod
    def _subject_scope(
        listing_id: int | None, product_id: int | None, seller_id: int | None
    ) -> tuple[str, int]:
        """Exactly one scope is required (400 otherwise)."""
        present = [
            listing_id is not None,
            product_id is not None,
            seller_id is not None,
        ]
        if present.count(True) != 1:
            raise ReviewValidationError(
                "provide exactly one of listing_id, product_id or seller_id"
            )
        if listing_id is not None:
            return ("listing", listing_id)
        if product_id is not None:
            return ("product", product_id)
        assert seller_id is not None
        return ("seller", seller_id)

    @staticmethod
    def _where_for_scope(scope: tuple[str, int]) -> list:
        kind, value = scope
        if kind == "listing":
            return [MarketplaceReview.listing_id == value]
        if kind == "product":
            return [MarketplaceReview.product_id == value]
        return [MarketplaceReview.seller_id == value]

    async def _summary_for_scope(self, scope: tuple[str, int]) -> RatingSummaryOut:
        rows = await self.db.execute(
            select(MarketplaceReview.rating, func.count(MarketplaceReview.id))
            .where(*self._where_for_scope(scope))
            .group_by(MarketplaceReview.rating)
        )
        counts = {rating: count for rating, count in rows.all()}
        distribution = {
            rating: counts.get(rating, 0) for rating in range(RATING_MAX, RATING_MIN - 1, -1)
        }
        total = sum(distribution.values())
        average = (
            round(sum(rating * count for rating, count in distribution.items()) / total, 2)
            if total
            else 0.0
        )
        return RatingSummaryOut(average=average, total=total, distribution=distribution)

    async def _resolve_target(
        self, listing_id: int | None, product_id: int | None
    ) -> tuple[CropListing | None, Product | None, int]:
        """Exactly one target referencing a real item; returns the item(s) and
        the derived seller id (400 on any violation)."""
        if (listing_id is None) == (product_id is None):
            raise ReviewValidationError("provide exactly one of listing_id or product_id")
        if listing_id is not None:
            listing = await self.db.get(CropListing, listing_id)
            if listing is None:
                raise ReviewValidationError("listing not found")
            return listing, None, listing.farmer_id
        product = await self.db.get(Product, product_id)
        if product is None:
            raise ReviewValidationError("product not found")
        return None, product, product.seller_id

    async def _find_by_target(
        self, reviewer_id: int, listing_id: int | None, product_id: int | None
    ) -> MarketplaceReview | None:
        return await self.db.scalar(
            select(MarketplaceReview).where(
                MarketplaceReview.reviewer_id == reviewer_id,
                MarketplaceReview.listing_id.is_(listing_id),
                MarketplaceReview.product_id.is_(product_id),
            )
        )

    async def _for_owner(self, review_id: int, user_id: int) -> MarketplaceReview:
        """Fetch a review the caller actually wrote. Anything else — missing id
        or another user's review — answers ``404`` (enumeration guard)."""
        review = await self.db.get(MarketplaceReview, review_id)
        if review is None or review.reviewer_id != user_id:
            raise ReviewNotFoundError(f"review {review_id} not found")
        return review

    async def _reviewer_names(self, user_ids: set[int]) -> dict[int, str]:
        if not user_ids:
            return {}
        rows = await self.db.scalars(select(User).where(User.id.in_(user_ids)))
        return {user.id: user.name for user in rows.all()}

    async def _build(
        self,
        review: MarketplaceReview,
        names: dict[int, str] | None = None,
    ) -> ReviewOut:
        """Assemble the payload. A review whose item has since been deleted
        keeps its text/reviewer but carries ``listing``/``product`` = None."""
        if names is None:
            names = await self._reviewer_names({review.reviewer_id})
        return ReviewOut(
            id=review.id,
            reviewer_id=review.reviewer_id,
            reviewer_name=names.get(review.reviewer_id, ""),
            seller_id=review.seller_id,
            rating=review.rating,
            title=review.title,
            content=review.content,
            created_at=review.created_at,
            updated_at=review.updated_at,
            listing=await self._listing_ref(review.listing_id),
            product=await self._product_ref(review.product_id),
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
