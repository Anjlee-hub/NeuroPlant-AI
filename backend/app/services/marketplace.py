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
    ProductDetailOut,
    ProductIn,
    ProductOut,
    ProductPageOut,
    ProductStatsOut,
    ProductUpdate,
    SellerOut,
    SellerRegister,
    SellerUpdate,
    ShopSummaryOut,
)
from app.services.reviews import ReviewsService
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
        """Persist one or more listing photos and return their public URLs."""
        return await self._persist_images(
            user, files, subdir="marketplace", max_files=MAX_LISTING_IMAGES
        )

    async def _persist_images(
        self, user: User, files: list[UploadFile], *, subdir: str, max_files: int
    ) -> list[str]:
        """Shared image pipeline: count / content-type / size checks, PIL decode
        so a renamed text file can't sneak through as "an image", then store via
        the platform's object-storage abstraction (local disk today, S3 in M11)
        under a user-scoped subdir. Raises :class:`ListingImageUploadError` for
        every reject path."""
        if not files:
            raise ListingImageUploadError("at least one image is required")
        if len(files) > max_files:
            raise ListingImageUploadError(f"at most {max_files} images per upload")

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
            key = storage.save(data, content_type, user.id, subdir=subdir)
            urls.append(storage.url(key))
        logger.info("images_uploaded", user_id=user.id, subdir=subdir, count=len(urls))
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
        """One listing with its farmer attached (for the detail view). The
        farmer's ``rating`` / ``review_count`` are review-driven (M4 Task 6)."""
        listing = await self.db.get(CropListing, listing_id)
        if listing is None:
            raise CropListingNotFoundError(f"crop listing {listing_id} not found")
        farmer = await self.db.get(User, listing.farmer_id)
        reputation = await ReviewsService(self.db).rating_summary(listing.farmer_id)
        out = CropListingDetailOut(
            **CropListingOut.model_validate(listing).model_dump(),
            farmer=FarmerSummaryOut(
                id=listing.farmer_id,
                name=farmer.name if farmer is not None else "",
                verified=farmer.verified if farmer is not None else False,
                rating=reputation.average,
                review_count=reputation.total,
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
            organic=payload.organic,
            manufacturer=payload.manufacturer,
            usage_instructions=payload.usage_instructions,
            availability=payload.availability,
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

    async def update_shop(self, user: User, payload: SellerUpdate) -> SellerOut:
        """Edit the seller's shop profile (M4 Task 4). Only the fields sent are
        changed; ``shop()`` re-assembles the full shop payload."""
        profile = await self._profile_for_user(user.id)
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(profile, field, value)
        self.db.add(profile)
        await self.db.commit()
        await self.db.refresh(profile)
        logger.info("shop_updated", user_id=user.id, profile_id=profile.id)
        return await self.shop(user)

    async def delete_product(self, user: User, product_id: int) -> None:
        """Remove one of the seller's own products (M4 Task 4)."""
        product = await self._product_for_seller(product_id, user.id)
        await self.db.delete(product)
        await self.db.commit()
        logger.info("product_deleted", seller_id=user.id, product_id=product_id)

    async def my_products_stats(self, user: User) -> ProductStatsOut:
        """Dashboard counts over the seller's own catalog (M4 Task 4)."""
        rows = await self.db.execute(
            select(Product.availability, func.count(Product.id))
            .where(Product.seller_id == user.id)
            .group_by(Product.availability)
        )
        by_status = {avail: count for avail, count in rows.all()}
        in_stock = by_status.get("in_stock", 0)
        out_of_stock = by_status.get("out_of_stock", 0)
        archived = by_status.get("archived", 0)
        return ProductStatsOut(
            total=in_stock + out_of_stock + archived,
            active=in_stock,
            out_of_stock=out_of_stock,
            archived=archived,
        )

    async def upload_shop_image(self, user: User, file: UploadFile, kind: str) -> str:
        """Persist the shop's logo or banner and return its public URL (M4 Task
        4). The caller drops the returned URL into the shop profile's
        ``logo_url`` / ``banner_url``."""
        urls = await self._persist_images(user, [file], subdir=f"shop/{kind}", max_files=1)
        return urls[0]

    async def upload_product_images(self, user: User, files: list[UploadFile]) -> list[str]:
        """Persist one or more product photos and return their public URLs (M4
        Task 4), to drop into the product's ``images`` field."""
        return await self._persist_images(
            user, files, subdir="products", max_files=MAX_LISTING_IMAGES
        )

    # ── Public product market (M4 Task 4) ────────────────────────────────

    async def browse_products(
        self,
        *,
        q: str | None = None,
        category: str | None = None,
        organic: bool | None = None,
        availability: str | None = None,
        min_price: float | None = None,
        max_price: float | None = None,
        brand: str | None = None,
        sort: str = SORT_NEWEST,
        page: int = 1,
        page_size: int = DEFAULT_PAGE_SIZE,
    ) -> ProductPageOut:
        """Paginated public product feed — search + filter + sort, server-side.
        Mirrors ``browse_crops`` so the two marketplaces share one query shape.
        ``q`` matches name / brand / description / manufacturer."""
        conds = self._product_filters(
            q=q,
            category=category,
            organic=organic,
            availability=availability,
            min_price=min_price,
            max_price=max_price,
            brand=brand,
        )
        page = max(1, page)
        page_size = max(1, min(page_size, MAX_PAGE_SIZE))

        total = int(await self.db.scalar(select(func.count(Product.id)).where(*conds)) or 0)
        rows = await self.db.scalars(
            select(Product)
            .where(*conds)
            .order_by(*self._product_sort(sort))
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        items = [ProductOut.model_validate(row) for row in rows.all()]
        return ProductPageOut(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            pages=ceil(total / page_size) if total else 0,
        )

    async def product_detail(self, product_id: int) -> ProductDetailOut:
        """One product with its shop attached (for the public detail view). The
        shop's ``rating`` is review-driven (M4 Task 6), computed live."""
        product = await self.db.get(Product, product_id)
        if product is None:
            raise ProductNotFoundError(f"product {product_id} not found")
        profile = await self.db.scalar(
            select(SellerProfile).where(SellerProfile.user_id == product.seller_id)
        )
        reputation = await ReviewsService(self.db).rating_summary(product.seller_id)
        return ProductDetailOut(
            **ProductOut.model_validate(product).model_dump(),
            shop=ShopSummaryOut(
                user_id=product.seller_id,
                shop_name=profile.shop_name if profile is not None else None,
                verified=profile.verified if profile is not None else False,
                rating=reputation.average,
                delivery_available=profile.delivery_available if profile is not None else False,
            ),
        )

    # ── Internals ────────────────────────────────────────────────────────

    async def shop(self, user: User) -> SellerOut:
        """Assemble the shop payload (profile + owner name + products). The
        ``rating`` is review-driven (M4 Task 6), computed live — the stored
        ``profile.rating`` placeholder is never read as the source of truth."""
        profile = await self._profile_for_user(user.id)
        products = await self.shop_products(user)
        reputation = await ReviewsService(self.db).rating_summary(user.id)
        return SellerOut(
            user_id=user.id,
            owner_name=user.name,
            shop_name=profile.shop_name,
            address=profile.address,
            phone=profile.phone,
            delivery_available=profile.delivery_available,
            rating=reputation.average,
            verified=profile.verified,
            created_at=profile.created_at,
            description=profile.description,
            opening_hours=profile.opening_hours,
            logo_url=profile.logo_url,
            banner_url=profile.banner_url,
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

    @staticmethod
    def _product_filters(
        *,
        q: str | None,
        category: str | None,
        organic: bool | None,
        availability: str | None,
        min_price: float | None,
        max_price: float | None,
        brand: str | None,
    ) -> list:
        """Search/filter conditions for the public product market (M4 Task 4).
        Mirrors ``_filter_conditions`` for crops: archived products stay hidden
        from the default feed unless explicitly requested."""
        conds = []
        if availability is None:
            conds.append(Product.availability != AVAILABILITY_ARCHIVED)
        if q:
            like = f"%{q}%"
            conds.append(
                or_(
                    Product.name.ilike(like),
                    Product.brand.ilike(like),
                    Product.description.ilike(like),
                    Product.manufacturer.ilike(like),
                )
            )
        if category:
            conds.append(Product.category == category)
        if organic is not None:
            conds.append(Product.organic == organic)
        if availability:
            conds.append(Product.availability == availability)
        if min_price is not None:
            conds.append(Product.price >= min_price)
        if max_price is not None:
            conds.append(Product.price <= max_price)
        if brand:
            conds.append(Product.brand.ilike(f"%{brand}%"))
        return conds

    @staticmethod
    def _product_sort(sort: str) -> list:
        if sort == SORT_OLDEST:
            return [Product.created_at.asc(), Product.id.asc()]
        if sort == SORT_PRICE_ASC:
            return [Product.price.asc(), Product.id.asc()]
        if sort == SORT_PRICE_DESC:
            return [Product.price.desc(), Product.id.desc()]
        return [Product.created_at.desc(), Product.id.desc()]
