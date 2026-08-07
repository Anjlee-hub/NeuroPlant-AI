"""Farmer marketplace service (M4, Task 1).

One service owns every marketplace rule so the routers only map HTTP
semantics. Three roles feed it:

* **Farmers** create/update/delete their own ``CropListing`` rows and list
  their own crops.
* **Customers** (any authenticated user) browse, search and filter listings
  and view a listing's detail (with its farmer).
* **Sellers** register/refresh their shop profile and manage their
  ``Product`` catalog. The shop *is* the existing ``SellerProfile`` row — this
  service is where the marketplace extends it, never a second seller table.

Ownership guards mirror the rest of the platform: a row that isn't yours
(and any missing row) answers ``404`` so ids can't be enumerated, the same
guard scans/recovery/calendar use. Browse/search share one query builder so
filter semantics never diverge between the two endpoints.
"""

from __future__ import annotations

import io
from datetime import date, datetime, time
from math import ceil

from fastapi import UploadFile
from PIL import Image
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.marketplace import CropListing, Product
from app.models.user import SellerProfile, User
from app.schemas.marketplace import (
    CropListingDetailOut,
    CropListingIn,
    CropListingOut,
    CropListingPageOut,
    CropListingStatsOut,
    CropListingUpdate,
    FarmerSummaryOut,
    ProductIn,
    ProductOut,
    ProductUpdate,
    SellerOut,
    SellerRegister,
)
from app.services.storage import get_storage_service

logger = get_logger(__name__)

# ── Pagination ────────────────────────────────────────────────────────────
DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100

# Sort keys accepted by the browse endpoint. ``oldest`` is the M4 Task 3
# additive extension (the buyer storefront needs oldest-first in addition to
# the Task 1 newest/price sorts); everything else is unchanged.
SORT_NEWEST = "newest"
SORT_OLDEST = "oldest"
SORT_PRICE_ASC = "price_asc"
SORT_PRICE_DESC = "price_desc"
SORT_KEYS = (SORT_NEWEST, SORT_OLDEST, SORT_PRICE_ASC, SORT_PRICE_DESC)

# The public browse feed hides archived listings unless a caller asks for them
# explicitly (M4 Task 3): ``archived`` means "hidden from the market" per Task
# 2, so the buyer storefront shouldn't surface retired listings by default.
AVAILABILITY_ARCHIVED = "archived"

# ── Listing image upload (M4, Task 2) ─────────────────────────────────────
MAX_LISTING_IMAGES = 8  # matches the schema's images list cap
MAX_LISTING_IMAGE_BYTES = 10 * 1024 * 1024  # 10 MB per image
IMAGE_CONTENT_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
    "image/bmp",
    "image/gif",
    "image/tiff",
}


class CropListingNotFoundError(Exception):
    """No crop listing with this id (or none owned by this farmer)."""


class ProductNotFoundError(Exception):
    """No product with this id on this seller's catalog."""


class SellerShopNotFoundError(Exception):
    """The user has no registered shop profile (role seller without a profile)."""


class ListingImageUploadError(Exception):
    """A listing image failed validation (type / size / not decodable)."""


class MarketplaceService:
    """Reads/writes marketplace rows and assembles page/detail payloads."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ── Farmer: listing lifecycle ────────────────────────────────────────

    async def create_listing(self, user: User, payload: CropListingIn) -> CropListingOut:
        """Offer the farmer's produce for sale (owned by ``user``)."""
        listing = CropListing(
            farmer_id=user.id,
            crop_name=payload.crop_name,
            category=payload.category,
            variety=payload.variety,
            quantity=payload.quantity,
            unit=payload.unit,
            price=payload.price,
            description=payload.description,
            images=payload.images,
            harvest_date=payload.harvest_date,
            organic=payload.organic,
            location=payload.location,
            availability=payload.availability,
        )
        self.db.add(listing)
        await self.db.commit()
        await self.db.refresh(listing)
        logger.info("crop_listing_created", farmer_id=user.id, listing_id=listing.id)
        return CropListingOut.model_validate(listing)

    async def update_listing(
        self, user: User, listing_id: int, payload: CropListingUpdate
    ) -> CropListingOut:
        """Partial edit of one of the farmer's own listings."""
        listing = await self._listing_for_farmer(listing_id, user.id)
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(listing, field, value)
        self.db.add(listing)
        await self.db.commit()
        await self.db.refresh(listing)
        logger.info("crop_listing_updated", farmer_id=user.id, listing_id=listing.id)
        return CropListingOut.model_validate(listing)

    async def delete_listing(self, user: User, listing_id: int) -> None:
        """Remove one of the farmer's own listings."""
        listing = await self._listing_for_farmer(listing_id, user.id)
        await self.db.delete(listing)
        await self.db.commit()
        logger.info("crop_listing_deleted", farmer_id=user.id, listing_id=listing_id)

    async def my_listings(self, user: User) -> list[CropListingOut]:
        """Every listing the farmer owns (newest first)."""
        rows = await self.db.scalars(
            select(CropListing)
            .where(CropListing.farmer_id == user.id)
            .order_by(CropListing.created_at.desc(), CropListing.id.desc())
        )
        return [CropListingOut.model_validate(row) for row in rows.all()]

    async def my_listings_stats(self, user: User) -> CropListingStatsOut:
        """Dashboard counts over the farmer's own listings (M4, Task 2)."""
        rows = await self.db.execute(
            select(CropListing.availability, func.count(CropListing.id))
            .where(CropListing.farmer_id == user.id)
            .group_by(CropListing.availability)
        )
        by_status = {avail: count for avail, count in rows.all()}
        available = by_status.get("available", 0)
        limited = by_status.get("limited", 0)
        sold = by_status.get("sold_out", 0)
        archived = by_status.get("archived", 0)
        return CropListingStatsOut(
            total=available + limited + sold + archived,
            active=available + limited,
            sold=sold,
            archived=archived,
        )

    async def upload_listing_images(self, user: User, files: list[UploadFile]) -> list[str]:
        """Persist one or more listing photos and return their public URLs.

        Validates count, content type and size, then decodes each file with
        PIL so a renamed text file can't sneak through as "an image". Files are
        stored via the platform's object-storage abstraction (local disk today,
        S3 in M11) under a user-scoped ``marketplace`` subdir.
        """
        if not files:
            raise ListingImageUploadError("at least one image is required")
        if len(files) > MAX_LISTING_IMAGES:
            raise ListingImageUploadError(f"at most {MAX_LISTING_IMAGES} images per listing")

        storage = get_storage_service()
        urls: list[str] = []
        for file in files:
            content_type = (file.content_type or "").split(";")[0].strip().lower()
            if content_type not in IMAGE_CONTENT_TYPES:
                raise ListingImageUploadError(
                    f"unsupported image type: {content_type or 'unknown'}"
                )
            data = await file.read()
            if not data:
                raise ListingImageUploadError("image file is empty")
            if len(data) > MAX_LISTING_IMAGE_BYTES:
                raise ListingImageUploadError("image exceeds the 10 MB limit")
            self._verify_image(data)
            key = storage.save(data, content_type, user.id, subdir="marketplace")
            urls.append(storage.url(key))
        logger.info("listing_images_uploaded", user_id=user.id, count=len(urls))
        return urls

    @staticmethod
    def _verify_image(data: bytes) -> None:
        """Decode + verify the bytes are a real image (rejects text-as-image)."""
        try:
            with Image.open(io.BytesIO(data)) as image:
                image.verify()
        except Exception as exc:
            raise ListingImageUploadError("file is not a valid image") from exc

    # ── Customer: browse / search / filter / detail ─────────────────────

    async def browse_crops(
        self,
        *,
        q: str | None = None,
        category: str | None = None,
        organic: bool | None = None,
        availability: str | None = None,
        min_price: float | None = None,
        max_price: float | None = None,
        location: str | None = None,
        harvest_from: date | None = None,
        harvest_to: date | None = None,
        sort: str = SORT_NEWEST,
        page: int = 1,
        page_size: int = DEFAULT_PAGE_SIZE,
    ) -> CropListingPageOut:
        """Paginated listing feed. ``q`` is the search term; every other
        keyword is a filter. One query builder serves both the browse and
        search endpoints so their semantics can't drift. ``harvest_from`` /
        ``harvest_to`` bound the listing's harvest date to a window (M4 Task 3
        additive extension)."""
        conds = self._filter_conditions(
            q=q,
            category=category,
            organic=organic,
            availability=availability,
            min_price=min_price,
            max_price=max_price,
            location=location,
            harvest_from=harvest_from,
            harvest_to=harvest_to,
        )
        page = max(1, page)
        page_size = max(1, min(page_size, MAX_PAGE_SIZE))

        total = int(await self.db.scalar(select(func.count(CropListing.id)).where(*conds)) or 0)
        rows = await self.db.scalars(
            select(CropListing)
            .where(*conds)
            .order_by(*self._sort_clauses(sort))
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        items = [CropListingOut.model_validate(row) for row in rows.all()]
        return CropListingPageOut(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            pages=ceil(total / page_size) if total else 0,
        )

    async def listing_detail(self, listing_id: int) -> CropListingDetailOut:
        """One listing with its farmer attached (for the detail view)."""
        listing = await self.db.get(CropListing, listing_id)
        if listing is None:
            raise CropListingNotFoundError(f"crop listing {listing_id} not found")
        farmer = await self.db.get(User, listing.farmer_id)
        out = CropListingDetailOut(
            **CropListingOut.model_validate(listing).model_dump(),
            farmer=FarmerSummaryOut(
                id=listing.farmer_id,
                name=farmer.name if farmer is not None else "",
                verified=farmer.verified if farmer is not None else False,
            ),
        )
        return out

    # ── Seller: shop registration + product catalog ─────────────────────

    async def register_shop(self, user: User, payload: SellerRegister) -> SellerOut:
        """Fill in / refresh the seller's shop profile (the ``SellerProfile``
        row auto-created at registration)."""
        profile = await self._profile_for_user(user.id)
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(profile, field, value)
        self.db.add(profile)
        await self.db.commit()
        await self.db.refresh(profile)
        logger.info("shop_registered", user_id=user.id, profile_id=profile.id)
        return await self.shop(user)

    async def my_shop(self, user: User) -> SellerOut:
        """The seller's own shop with its product catalog attached."""
        return await self.shop(user)

    async def add_product(self, user: User, payload: ProductIn) -> ProductOut:
        """Add one agricultural input to the seller's catalog.

        The seller's ``SellerProfile`` always exists (auto-created at
        registration), so a product can be listed before the shop profile is
        filled in — the product only needs the seller's user id.
        """
        product = Product(
            seller_id=user.id,
            name=payload.name,
            category=payload.category,
            brand=payload.brand,
            description=payload.description,
            price=payload.price,
            unit=payload.unit,
            stock_quantity=payload.stock_quantity,
            images=payload.images,
        )
        self.db.add(product)
        await self.db.commit()
        await self.db.refresh(product)
        logger.info("product_added", seller_id=user.id, product_id=product.id)
        return ProductOut.model_validate(product)

    async def update_product(
        self, user: User, product_id: int, payload: ProductUpdate
    ) -> ProductOut:
        """Partial edit of one of the seller's own products."""
        product = await self._product_for_seller(product_id, user.id)
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(product, field, value)
        self.db.add(product)
        await self.db.commit()
        await self.db.refresh(product)
        logger.info("product_updated", seller_id=user.id, product_id=product.id)
        return ProductOut.model_validate(product)

    async def shop_products(self, user: User) -> list[ProductOut]:
        """The seller's product catalog (newest first)."""
        rows = await self.db.scalars(
            select(Product)
            .where(Product.seller_id == user.id)
            .order_by(Product.created_at.desc(), Product.id.desc())
        )
        return [ProductOut.model_validate(row) for row in rows.all()]

    # ── Internals ────────────────────────────────────────────────────────

    async def shop(self, user: User) -> SellerOut:
        """Assemble the shop payload (profile + owner name + products)."""
        profile = await self._profile_for_user(user.id)
        products = await self.shop_products(user)
        return SellerOut(
            user_id=user.id,
            owner_name=user.name,
            shop_name=profile.shop_name,
            address=profile.address,
            phone=profile.phone,
            delivery_available=profile.delivery_available,
            rating=profile.rating,
            verified=profile.verified,
            created_at=profile.created_at,
            products=products,
        )

    async def _profile_for_user(self, user_id: int) -> SellerProfile:
        profile = await self.db.scalar(
            select(SellerProfile).where(SellerProfile.user_id == user_id)
        )
        if profile is None:
            raise SellerShopNotFoundError(f"no shop registered for user {user_id}")
        return profile

    async def _listing_for_farmer(self, listing_id: int, farmer_id: int) -> CropListing:
        listing = await self.db.scalar(
            select(CropListing).where(
                CropListing.id == listing_id,
                CropListing.farmer_id == farmer_id,
            )
        )
        if listing is None:
            raise CropListingNotFoundError(
                f"crop listing {listing_id} not found for farmer {farmer_id}"
            )
        return listing

    async def _product_for_seller(self, product_id: int, seller_id: int) -> Product:
        product = await self.db.scalar(
            select(Product).where(
                Product.id == product_id,
                Product.seller_id == seller_id,
            )
        )
        if product is None:
            raise ProductNotFoundError(f"product {product_id} not found for seller {seller_id}")
        return product

    @staticmethod
    def _filter_conditions(
        *,
        q: str | None,
        category: str | None,
        organic: bool | None,
        availability: str | None,
        min_price: float | None,
        max_price: float | None,
        location: str | None,
        harvest_from: date | None = None,
        harvest_to: date | None = None,
    ) -> list:
        conds = []
        # Archived listings are off the market: hide them from the default
        # feed, but let an explicit availability=archived filter (used by the
        # buyer's availability select) still reach them.
        if availability is None:
            conds.append(CropListing.availability != AVAILABILITY_ARCHIVED)
        if q:
            like = f"%{q}%"
            conds.append(
                or_(
                    CropListing.crop_name.ilike(like),
                    CropListing.variety.ilike(like),
                    CropListing.description.ilike(like),
                    CropListing.location.ilike(like),
                )
            )
        if category:
            conds.append(CropListing.category == category)
        if organic is not None:
            conds.append(CropListing.organic == organic)
        if availability:
            conds.append(CropListing.availability == availability)
        if min_price is not None:
            conds.append(CropListing.price >= min_price)
        if max_price is not None:
            conds.append(CropListing.price <= max_price)
        if location:
            conds.append(CropListing.location.ilike(f"%{location}%"))
        # Harvest window: listings harvested between (inclusive) the two dates.
        # Listings with no harvest date fall outside any window, matching how
        # a farmer who leaves the field blank isn't advertising a date.
        if harvest_from is not None:
            conds.append(CropListing.harvest_date >= datetime.combine(harvest_from, time.min))
        if harvest_to is not None:
            conds.append(CropListing.harvest_date <= datetime.combine(harvest_to, time.max))
        return conds

    @staticmethod
    def _sort_clauses(sort: str) -> list:
        if sort == SORT_OLDEST:
            return [CropListing.created_at.asc(), CropListing.id.asc()]
        if sort == SORT_PRICE_ASC:
            return [CropListing.price.asc(), CropListing.id.asc()]
        if sort == SORT_PRICE_DESC:
            return [CropListing.price.desc(), CropListing.id.desc()]
        return [CropListing.created_at.desc(), CropListing.id.desc()]
