"""Marketplace favourites service (M4, Task 6).

One service owns every saved-item rule so the router only maps HTTP semantics.

* Any authenticated user can save a crop listing or a product, list their saved
  items, and check/remove a single saved item.
* ``add`` is **idempotent** — saving an item that is already saved returns the
  existing row (no duplicate), which the unique constraints in the model back
  up at the database level.
* Ownership follows the platform convention: a favourite row that isn't the
  caller's (and any missing id) answers ``404`` so ids can't be enumerated —
  the same guard scans/recovery/calendar/messaging use.
* The exactly-one ``listing_id``/``product_id`` rule and existence checks are
  ``400`` validation errors (matching messaging's create-context handling —
  unknown references never leak).

Rows whose item has been deleted are filtered out of ``list`` — a saved copy of
a retired listing is meaningless to the user.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.marketplace import CropListing, Product
from app.models.marketplace_trust import MarketplaceFavorite
from app.models.user import User
from app.schemas.favorites import FavoriteCreate, FavoriteOut, FavoriteStatusOut
from app.schemas.marketplace import CropListingOut, ProductOut

logger = get_logger(__name__)


class FavoriteValidationError(Exception):
    """Bad favourite target — both/none/unknown listing or product."""


class FavoriteNotFoundError(Exception):
    """No favourite with this id — or one that isn't the caller's."""


class FavoritesService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def add(self, user: User, payload: FavoriteCreate) -> FavoriteOut:
        """Save an item (idempotent). Exactly one of ``listing_id`` /
        ``product_id`` must be provided and must reference a real item; saving
        an already-saved item returns the existing row."""
        await self._validate_target(payload.listing_id, payload.product_id)
        existing = await self._find(user.id, payload.listing_id, payload.product_id)
        if existing is not None:
            return await self._build(existing)
        favorite = MarketplaceFavorite(
            user_id=user.id,
            listing_id=payload.listing_id,
            product_id=payload.product_id,
        )
        self.db.add(favorite)
        await self.db.commit()
        await self.db.refresh(favorite)
        logger.info(
            "favorite_added",
            user_id=user.id,
            favorite_id=favorite.id,
            listing_id=payload.listing_id,
            product_id=payload.product_id,
        )
        return await self._build(favorite)

    async def remove(self, user: User, favorite_id: int) -> None:
        """Remove one of the caller's own saved items (404 for others')."""
        favorite = await self._for_user(favorite_id, user.id)
        await self.db.delete(favorite)
        await self.db.commit()
        logger.info("favorite_removed", user_id=user.id, favorite_id=favorite_id)

    async def list(self, user: User) -> list[FavoriteOut]:
        """The caller's saved items, newest first, with the full listing or
        product attached. Copies whose item has since been deleted are skipped
        (a dead saved copy is meaningless)."""
        rows = await self.db.scalars(
            select(MarketplaceFavorite)
            .where(MarketplaceFavorite.user_id == user.id)
            .order_by(MarketplaceFavorite.created_at.desc(), MarketplaceFavorite.id.desc())
        )
        items: list[FavoriteOut] = []
        for row in rows.all():
            built = await self._build(row)
            if built.listing is None and built.product is None:
                continue  # the saved item no longer exists
            items.append(built)
        return items

    async def status(
        self, user: User, *, listing_id: int | None, product_id: int | None
    ) -> FavoriteStatusOut:
        """Whether the caller has saved the requested item (button state).

        The target must exist (400 otherwise) — status for a deleted item is
        not meaningful and would leak an id boundary.
        """
        await self._validate_target(listing_id, product_id)
        favorite = await self._find(user.id, listing_id, product_id)
        return FavoriteStatusOut(
            favorited=favorite is not None,
            favorite_id=favorite.id if favorite is not None else None,
            listing_id=listing_id,
            product_id=product_id,
        )

    # ── Internals ────────────────────────────────────────────────────────

    async def _validate_target(self, listing_id: int | None, product_id: int | None) -> None:
        """Exactly one context, referencing a real item (400 otherwise)."""
        if (listing_id is None) == (product_id is None):
            raise FavoriteValidationError("provide exactly one of listing_id or product_id")
        if listing_id is not None:
            listing = await self.db.get(CropListing, listing_id)
            if listing is None:
                raise FavoriteValidationError("listing not found")
        else:
            product = await self.db.get(Product, product_id)
            if product is None:
                raise FavoriteValidationError("product not found")

    async def _find(
        self, user_id: int, listing_id: int | None, product_id: int | None
    ) -> MarketplaceFavorite | None:
        """The caller's saved row for this target, if one exists."""
        return await self.db.scalar(
            select(MarketplaceFavorite).where(
                MarketplaceFavorite.user_id == user_id,
                MarketplaceFavorite.listing_id.is_(listing_id),
                MarketplaceFavorite.product_id.is_(product_id),
            )
        )

    async def _for_user(self, favorite_id: int, user_id: int) -> MarketplaceFavorite:
        """Fetch a saved row the caller actually owns. Anything else — missing
        id or another user's row — answers ``404`` (enumeration guard)."""
        favorite = await self.db.get(MarketplaceFavorite, favorite_id)
        if favorite is None or favorite.user_id != user_id:
            raise FavoriteNotFoundError(f"favorite {favorite_id} not found")
        return favorite

    async def _build(self, favorite: MarketplaceFavorite) -> FavoriteOut:
        """Attach the full listing or product to a saved row."""
        if favorite.listing_id is not None:
            listing = await self.db.get(CropListing, favorite.listing_id)
            return FavoriteOut(
                id=favorite.id,
                created_at=favorite.created_at,
                listing=CropListingOut.model_validate(listing) if listing is not None else None,
            )
        product = await self.db.get(Product, favorite.product_id)
        return FavoriteOut(
            id=favorite.id,
            created_at=favorite.created_at,
            product=ProductOut.model_validate(product) if product is not None else None,
        )
