"""Marketplace schemas (M4, Task 1).

Request/response DTOs for the farmer marketplace. Vocabularies (crop
categories, product categories, units, availability) are validated here at the
boundary; ownership and business rules live in ``app.services.marketplace``.
All ``*Update`` models are partial (``exclude_unset``) so sending only the
changed fields edits just those.
"""

from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

# ── Vocabularies (validated at the boundary) ──────────────────────────────
#
# ``archived`` was added in M4 Task 2 (additive extension) so farmers can
# retire a listing without deleting it; the dashboard's "archived" bucket and
# the mark-as-archived action both map to this value. Existing values are
# unchanged, so the Task 1 contract is backward compatible.

CROP_CATEGORIES = ("vegetable", "fruit", "grain", "pulses", "spice", "other")
PRODUCT_CATEGORIES = ("fertilizer", "pesticide", "seed", "tool")
AVAILABILITY = ("available", "limited", "sold_out", "archived")
UNITS = ("kg", "g", "qtl", "bag", "dozen", "piece", "l", "box", "bundle")

_CROP_CATEGORY_PATTERN = "^(vegetable|fruit|grain|pulses|spice|other)$"
_PRODUCT_CATEGORY_PATTERN = "^(fertilizer|pesticide|seed|tool)$"
_AVAILABILITY_PATTERN = "^(available|limited|sold_out|archived)$"
_UNIT_PATTERN = "^(kg|g|qtl|bag|dozen|piece|l|box|bundle)$"

# A single image is a URL-ish string; lists are capped so one listing can't
# carry an unbounded payload.
ImageUrl = Annotated[str, Field(min_length=1, max_length=500)]


# ── Crop listings (farmer ↔ customer) ─────────────────────────────────────


class CropListingIn(BaseModel):
    """POST /marketplace/crops — offer produce for sale."""

    crop_name: str = Field(min_length=1, max_length=120)
    category: str = Field(pattern=_CROP_CATEGORY_PATTERN)
    variety: str | None = Field(default=None, max_length=120)
    quantity: float = Field(gt=0, description="Quantity offered")
    unit: str = Field(pattern=_UNIT_PATTERN)
    price: float = Field(ge=0, description="Price per unit")
    description: str | None = Field(default=None, max_length=2000)
    images: list[ImageUrl] | None = Field(default=None, max_length=8)
    harvest_date: datetime | None = Field(default=None)
    organic: bool = Field(default=False)
    location: str | None = Field(default=None, max_length=200)
    availability: str = Field(default="available", pattern=_AVAILABILITY_PATTERN)


class CropListingUpdate(BaseModel):
    """PATCH /marketplace/crops/{id} — partial edit of a listing."""

    crop_name: str | None = Field(default=None, min_length=1, max_length=120)
    category: str | None = Field(default=None, pattern=_CROP_CATEGORY_PATTERN)
    variety: str | None = Field(default=None, max_length=120)
    quantity: float | None = Field(default=None, gt=0)
    unit: str | None = Field(default=None, pattern=_UNIT_PATTERN)
    price: float | None = Field(default=None, ge=0)
    description: str | None = Field(default=None, max_length=2000)
    images: list[ImageUrl] | None = Field(default=None, max_length=8)
    harvest_date: datetime | None = Field(default=None)
    organic: bool | None = Field(default=None)
    location: str | None = Field(default=None, max_length=200)
    availability: str | None = Field(default=None, pattern=_AVAILABILITY_PATTERN)


class CropListingOut(BaseModel):
    """One listing as returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    farmer_id: int
    crop_name: str
    category: str
    variety: str | None
    quantity: float
    unit: str
    price: float
    description: str | None
    images: list[str] | None
    harvest_date: datetime | None
    organic: bool
    location: str | None
    availability: str
    created_at: datetime
    updated_at: datetime


class FarmerSummaryOut(BaseModel):
    """Compact farmer identity attached to a listing's detail view."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    verified: bool


class CropListingDetailOut(CropListingOut):
    """GET /marketplace/crops/{id} — full listing plus its farmer."""

    farmer: FarmerSummaryOut


class CropListingPageOut(BaseModel):
    """Paginated browse/search result."""

    items: list[CropListingOut] = Field(default_factory=list)
    total: int = Field(ge=0)
    page: int = Field(ge=1)
    page_size: int = Field(ge=1)
    pages: int = Field(ge=0)


class CropListingStatsOut(BaseModel):
    """Dashboard summary counts for the farmer's own listings (M4, Task 2).

    ``active`` counts everything still offered for sale (``available`` +
    ``limited``); ``sold`` is ``sold_out``; ``archived`` is ``archived``;
    ``total`` is every listing the farmer owns.
    """

    total: int = Field(ge=0)
    active: int = Field(ge=0)
    sold: int = Field(ge=0)
    archived: int = Field(ge=0)


class ListingImagesOut(BaseModel):
    """Response for the multi-image upload endpoint — persisted media URLs.

    URLs are storage-relative (``/media/...``) and go straight into the
    ``images`` field of a listing payload.
    """

    urls: list[str] = Field(default_factory=list)


# ── Seller shop ───────────────────────────────────────────────────────────


class SellerRegister(BaseModel):
    """POST /marketplace/shop/register — fill in the seller's shop profile.

    ``owner`` is the authenticated user (the shop's owner) and ``rating`` is a
    read-only, review-driven field (0.0 until a later task) — neither is set
    here.
    """

    shop_name: str = Field(min_length=1, max_length=200)
    address: str | None = Field(default=None, max_length=2000)
    phone: str | None = Field(default=None, max_length=20)
    delivery_available: bool = Field(default=False)


class SellerUpdate(BaseModel):
    """PATCH-able shape (reused by register for the first write) — partial."""

    shop_name: str | None = Field(default=None, min_length=1, max_length=200)
    address: str | None = Field(default=None, max_length=2000)
    phone: str | None = Field(default=None, max_length=20)
    delivery_available: bool | None = Field(default=None)


class SellerOut(BaseModel):
    """A shop as returned by the API, with its product catalog attached."""

    model_config = ConfigDict(from_attributes=True)

    user_id: int
    owner_name: str
    shop_name: str | None
    address: str | None
    phone: str | None
    delivery_available: bool
    rating: float = Field(ge=0)
    verified: bool
    created_at: datetime
    products: list["ProductOut"] = Field(default_factory=list)


# ── Products (seller ↔ customer) ──────────────────────────────────────────


class ProductIn(BaseModel):
    """POST /marketplace/shop/products — list an agricultural input for sale."""

    name: str = Field(min_length=1, max_length=200)
    category: str = Field(pattern=_PRODUCT_CATEGORY_PATTERN)
    brand: str | None = Field(default=None, max_length=120)
    description: str | None = Field(default=None, max_length=2000)
    price: float = Field(ge=0)
    unit: str = Field(pattern=_UNIT_PATTERN)
    stock_quantity: float | None = Field(default=None, ge=0)
    images: list[ImageUrl] | None = Field(default=None, max_length=8)


class ProductUpdate(BaseModel):
    """PATCH /marketplace/shop/products/{id} — partial edit of a product."""

    name: str | None = Field(default=None, min_length=1, max_length=200)
    category: str | None = Field(default=None, pattern=_PRODUCT_CATEGORY_PATTERN)
    brand: str | None = Field(default=None, max_length=120)
    description: str | None = Field(default=None, max_length=2000)
    price: float | None = Field(default=None, ge=0)
    unit: str | None = Field(default=None, pattern=_UNIT_PATTERN)
    stock_quantity: float | None = Field(default=None, ge=0)
    images: list[ImageUrl] | None = Field(default=None, max_length=8)


class ProductOut(BaseModel):
    """One product as returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    seller_id: int
    name: str
    category: str
    brand: str | None
    description: str | None
    price: float
    unit: str
    stock_quantity: float | None
    images: list[str] | None
    created_at: datetime
    updated_at: datetime


# SellerOut references ProductOut forward; resolve at import time.
SellerOut.model_rebuild()
