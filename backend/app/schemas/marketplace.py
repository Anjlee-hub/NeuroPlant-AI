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
# ``organic`` was added in M4 Task 4 (additive extension) so agricultural
# shops can list organic inputs alongside fertilizers / pesticides / seeds /
# tools. Existing values are unchanged, so the Task 1 contract is intact.
PRODUCT_CATEGORIES = ("fertilizer", "pesticide", "seed", "tool", "organic")
AVAILABILITY = ("available", "limited", "sold_out", "archived")
UNITS = ("kg", "g", "qtl", "bag", "dozen", "piece", "l", "box", "bundle")

# Product stock/archive lifecycle (M4 Task 4) — ``archived`` mirrors the crop
# listings convention; in/out of stock is the seller's day-to-day toggle.
PRODUCT_AVAILABILITY = ("in_stock", "out_of_stock", "archived")

_CROP_CATEGORY_PATTERN = "^(vegetable|fruit|grain|pulses|spice|other)$"
_PRODUCT_CATEGORY_PATTERN = "^(fertilizer|pesticide|seed|tool|organic)$"
_AVAILABILITY_PATTERN = "^(available|limited|sold_out|archived)$"
_PRODUCT_AVAILABILITY_PATTERN = "^(in_stock|out_of_stock|archived)$"
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
    here. The Seller Portal fields (description / opening_hours / logo_url /
    banner_url) are the M4 Task 4 additive extension.
    """

    shop_name: str = Field(min_length=1, max_length=200)
    address: str | None = Field(default=None, max_length=2000)
    phone: str | None = Field(default=None, max_length=20)
    delivery_available: bool = Field(default=False)
    description: str | None = Field(default=None, max_length=5000)
    opening_hours: str | None = Field(default=None, max_length=200)
    logo_url: str | None = Field(default=None, max_length=500)
    banner_url: str | None = Field(default=None, max_length=500)


class SellerUpdate(BaseModel):
    """PATCH /marketplace/shop/me — partial edit of the shop profile."""

    shop_name: str | None = Field(default=None, min_length=1, max_length=200)
    address: str | None = Field(default=None, max_length=2000)
    phone: str | None = Field(default=None, max_length=20)
    delivery_available: bool | None = Field(default=None)
    description: str | None = Field(default=None, max_length=5000)
    opening_hours: str | None = Field(default=None, max_length=200)
    logo_url: str | None = Field(default=None, max_length=500)
    banner_url: str | None = Field(default=None, max_length=500)


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
    description: str | None
    opening_hours: str | None
    logo_url: str | None
    banner_url: str | None
    products: list["ProductOut"] = Field(default_factory=list)


# ── Products (seller ↔ customer) ──────────────────────────────────────────


class ProductIn(BaseModel):
    """POST /marketplace/shop/products — list an agricultural input for sale.

    The Seller Portal fields (organic / manufacturer / usage_instructions /
    availability) are the M4 Task 4 additive extension; everything else is the
    Task 1 contract.
    """

    name: str = Field(min_length=1, max_length=200)
    category: str = Field(pattern=_PRODUCT_CATEGORY_PATTERN)
    brand: str | None = Field(default=None, max_length=120)
    description: str | None = Field(default=None, max_length=2000)
    price: float = Field(ge=0)
    unit: str = Field(pattern=_UNIT_PATTERN)
    stock_quantity: float | None = Field(default=None, ge=0)
    images: list[ImageUrl] | None = Field(default=None, max_length=8)
    organic: bool = Field(default=False)
    manufacturer: str | None = Field(default=None, max_length=200)
    usage_instructions: str | None = Field(default=None, max_length=5000)
    availability: str = Field(default="in_stock", pattern=_PRODUCT_AVAILABILITY_PATTERN)


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
    organic: bool | None = Field(default=None)
    manufacturer: str | None = Field(default=None, max_length=200)
    usage_instructions: str | None = Field(default=None, max_length=5000)
    availability: str | None = Field(default=None, pattern=_PRODUCT_AVAILABILITY_PATTERN)


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
    organic: bool
    manufacturer: str | None
    usage_instructions: str | None
    availability: str
    created_at: datetime
    updated_at: datetime


class ProductStatsOut(BaseModel):
    """Dashboard summary counts for the seller's own catalog (M4, Task 4).

    ``active`` is everything currently on sale (``in_stock``); ``out_of_stock``
    is the day-to-day gap; ``archived`` is retired products; ``total`` is every
    product the seller owns.
    """

    total: int = Field(ge=0)
    active: int = Field(ge=0)
    out_of_stock: int = Field(ge=0)
    archived: int = Field(ge=0)


class ShopSummaryOut(BaseModel):
    """Compact shop identity attached to a product's public detail view."""

    model_config = ConfigDict(from_attributes=True)

    user_id: int
    shop_name: str | None
    verified: bool
    rating: float = Field(ge=0)
    delivery_available: bool = False


class ProductDetailOut(ProductOut):
    """GET /marketplace/products/{id} — full product plus its shop."""

    shop: ShopSummaryOut


class ProductPageOut(BaseModel):
    """Paginated public product-marketplace result."""

    items: list[ProductOut] = Field(default_factory=list)
    total: int = Field(ge=0)
    page: int = Field(ge=1)
    page_size: int = Field(ge=1)
    pages: int = Field(ge=0)


# SellerOut references ProductOut forward; resolve at import time.
SellerOut.model_rebuild()
