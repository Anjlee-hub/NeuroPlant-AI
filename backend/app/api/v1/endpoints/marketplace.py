"""Farmer marketplace endpoints (M4, Task 1).

Three surfaces share the ``/marketplace`` prefix:

* **Farmers** (``farmer``/``admin``) create, update, delete and list their own
  crop listings.
* **Any authenticated user** (customers included) browses, searches, filters
  and opens listing details — read-only.
* **Sellers** (``seller``/``admin``) register their shop and manage their
  product catalog.

Role checks use ``require_roles`` so RBAC is enforced as a dependency; the
service owns every business rule (ownership guard answers ``404`` for other
users' rows, same as scans/recovery/calendar). ``/crops/mine`` and
``/crops/search`` are declared before ``/crops/{listing_id}`` so FastAPI never
reads them as an id.
"""

from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, File, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_current_user, require_roles
from app.db.session import get_db
from app.models.base import UserRole
from app.models.user import User
from app.schemas.marketplace import (
    CartItemIn,
    CartOut,
    CheckoutIn,
    CropListingDetailOut,
    CropListingIn,
    CropListingOut,
    CropListingPageOut,
    CropListingStatsOut,
    CropListingUpdate,
    ListingImagesOut,
    OrderOut,
    ProductDetailOut,
    ProductIn,
    ProductOut,
    ProductPageOut,
    ProductStatsOut,
    ProductUpdate,
    SellerOut,
    SellerRegister,
    SellerUpdate,
)
from app.services.marketplace import (
    DEFAULT_PAGE_SIZE,
    MAX_PAGE_SIZE,
    SORT_KEYS,
    SORT_NEWEST,
    MarketplaceService,
)

router = APIRouter(prefix="/marketplace", tags=["marketplace"])

Db = Annotated[AsyncSession, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]
FarmerUser = Annotated[User, Depends(require_roles(UserRole.FARMER, UserRole.ADMIN))]
SellerUser = Annotated[User, Depends(require_roles(UserRole.SELLER, UserRole.ADMIN))]


@router.get("/crops", response_model=CropListingPageOut)
async def browse_crops(
    user: CurrentUser,
    db: Db,
    q: str | None = Query(
        None, max_length=200, description="Search term over name/variety/description/location"
    ),
    category: str | None = Query(None, max_length=40, description="Filter: crop category"),
    organic: bool | None = Query(None, description="Filter: only organic produce"),
    availability: str | None = Query(None, max_length=20, description="Filter: availability"),
    min_price: float | None = Query(None, ge=0, description="Filter: minimum price per unit"),
    max_price: float | None = Query(None, ge=0, description="Filter: maximum price per unit"),
    location: str | None = Query(None, max_length=200, description="Filter: location substring"),
    harvest_from: date | None = Query(
        None, description="Filter: harvest date on/after this day (inclusive)"
    ),
    harvest_to: date | None = Query(
        None, description="Filter: harvest date on/before this day (inclusive)"
    ),
    sort: str = Query(SORT_NEWEST, pattern="|".join(SORT_KEYS), description="Sort order"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE, description="Items per page"),
) -> CropListingPageOut:
    """Browse the marketplace (paginated), optionally filtered by category /
    organic / availability / price range / location / harvest-date window and
    sorted newest / oldest / by price. Passing ``q`` searches at the same time.
    """
    return await MarketplaceService(db).browse_crops(
        q=q,
        category=category,
        organic=organic,
        availability=availability,
        min_price=min_price,
        max_price=max_price,
        location=location,
        harvest_from=harvest_from,
        harvest_to=harvest_to,
        sort=sort,
        page=page,
        page_size=page_size,
    )


@router.get("/crops/search", response_model=CropListingPageOut)
async def search_crops(
    user: CurrentUser,
    db: Db,
    q: str = Query(min_length=1, max_length=200, description="Required search term"),
    organic: bool | None = Query(None, description="Filter: only organic produce"),
    availability: str | None = Query(None, max_length=20, description="Filter: availability"),
    min_price: float | None = Query(None, ge=0, description="Filter: minimum price per unit"),
    max_price: float | None = Query(None, ge=0, description="Filter: maximum price per unit"),
    location: str | None = Query(None, max_length=200, description="Filter: location substring"),
    harvest_from: date | None = Query(
        None, description="Filter: harvest date on/after this day (inclusive)"
    ),
    harvest_to: date | None = Query(
        None, description="Filter: harvest date on/before this day (inclusive)"
    ),
    sort: str = Query(SORT_NEWEST, pattern="|".join(SORT_KEYS), description="Sort order"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE, description="Items per page"),
) -> CropListingPageOut:
    """Text search over crop name / variety / description / location. Shares
    the browse query builder, so filters apply identically to both."""
    return await MarketplaceService(db).browse_crops(
        q=q,
        organic=organic,
        availability=availability,
        min_price=min_price,
        max_price=max_price,
        location=location,
        harvest_from=harvest_from,
        harvest_to=harvest_to,
        sort=sort,
        page=page,
        page_size=page_size,
    )


@router.get("/crops/mine", response_model=list[CropListingOut])
async def my_crop_listings(user: FarmerUser, db: Db) -> list[CropListingOut]:
    """The farmer's own listings (newest first)."""
    return await MarketplaceService(db).my_listings(user)


@router.get("/crops/stats", response_model=CropListingStatsOut)
async def crop_listing_stats(user: FarmerUser, db: Db) -> CropListingStatsOut:
    """Dashboard summary counts (total / active / sold / archived) over the
    farmer's own listings (M4, Task 2)."""
    return await MarketplaceService(db).my_listings_stats(user)


@router.post("/crops/images", response_model=ListingImagesOut)
async def upload_listing_images(
    user: FarmerUser,
    db: Db,
    files: list[UploadFile] = File(description="Listing photos (JPEG/PNG/WebP, max 8)"),
) -> ListingImagesOut:
    """Upload one or more listing photos and get back storage URLs to drop
    into the listing's ``images`` field (M4, Task 2).

    Validated by type / size and decoded to reject non-images; ``422`` on any
    invalid file. The returned URLs are what a create/update listing payload
    sends as ``images``.
    """
    urls = await MarketplaceService(db).upload_listing_images(user, files)
    return ListingImagesOut(urls=urls)


@router.post("/crops", response_model=CropListingOut, status_code=status.HTTP_201_CREATED)
async def create_crop_listing(payload: CropListingIn, user: FarmerUser, db: Db) -> CropListingOut:
    """Offer the farmer's produce for sale."""
    return await MarketplaceService(db).create_listing(user, payload)


@router.get("/crops/{listing_id}", response_model=CropListingDetailOut)
async def get_crop_listing(listing_id: int, user: CurrentUser, db: Db) -> CropListingDetailOut:
    """One listing with its farmer attached (detail view). ``404`` when the
    listing doesn't exist."""
    return await MarketplaceService(db).listing_detail(listing_id)


@router.patch("/crops/{listing_id}", response_model=CropListingOut)
async def update_crop_listing(
    listing_id: int, payload: CropListingUpdate, user: FarmerUser, db: Db
) -> CropListingOut:
    """Partial edit of one of the farmer's own listings.

    Only the fields sent are changed; ``404`` for a listing the farmer doesn't
    own (enumeration guard).
    """
    return await MarketplaceService(db).update_listing(user, listing_id, payload)


@router.delete("/crops/{listing_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_crop_listing(listing_id: int, user: FarmerUser, db: Db) -> None:
    """Remove one of the farmer's own listings. ``204`` on success; ``404``
    for a listing the farmer doesn't own."""
    await MarketplaceService(db).delete_listing(user, listing_id)


@router.post("/shop/register", response_model=SellerOut)
async def register_shop(payload: SellerRegister, user: SellerUser, db: Db) -> SellerOut:
    """Register / refresh the seller's agricultural shop. ``owner`` is the
    authenticated seller and ``rating`` is review-driven (read-only), so shop
    name, address, phone, delivery availability and the M4 Task 4 Seller
    Portal fields (description / opening_hours / logo_url / banner_url) are
    all set here."""
    return await MarketplaceService(db).register_shop(user, payload)


@router.get("/shop/me", response_model=SellerOut)
async def get_my_shop(user: SellerUser, db: Db) -> SellerOut:
    """The seller's own shop profile with its product catalog attached."""
    return await MarketplaceService(db).my_shop(user)


@router.patch("/shop/me", response_model=SellerOut)
async def update_shop(payload: SellerUpdate, user: SellerUser, db: Db) -> SellerOut:
    """Partial edit of the seller's own shop profile (M4, Task 4).

    Only the fields sent are changed; the response re-attaches the product
    catalog, so the dashboard stays in sync after an edit.
    """
    return await MarketplaceService(db).update_shop(user, payload)


@router.get("/shop/products", response_model=list[ProductOut])
async def get_my_products(user: SellerUser, db: Db) -> list[ProductOut]:
    """The seller's full product catalog (newest first)."""
    return await MarketplaceService(db).shop_products(user)


@router.post("/shop/products/images", response_model=ListingImagesOut)
async def upload_product_images(
    user: SellerUser,
    db: Db,
    files: list[UploadFile] = File(description="Product photos (JPEG/PNG/WebP, max 8)"),
) -> ListingImagesOut:
    """Upload one or more product photos and get back storage URLs to drop
    into the product's ``images`` field (M4, Task 4). Same validation and
    ``422`` contract as the crop-listing image upload."""
    urls = await MarketplaceService(db).upload_product_images(user, files)
    return ListingImagesOut(urls=urls)


@router.get("/shop/products/stats", response_model=ProductStatsOut)
async def product_stats(user: SellerUser, db: Db) -> ProductStatsOut:
    """Dashboard summary counts (total / active / out of stock / archived)
    over the seller's own catalog (M4, Task 4)."""
    return await MarketplaceService(db).my_products_stats(user)


@router.post("/shop/products", response_model=ProductOut, status_code=status.HTTP_201_CREATED)
async def add_product(payload: ProductIn, user: SellerUser, db: Db) -> ProductOut:
    """Add one agricultural input (fertilizer / pesticide / seed / tool /
    organic) to the seller's catalog."""
    return await MarketplaceService(db).add_product(user, payload)


@router.patch("/shop/products/{product_id}", response_model=ProductOut)
async def update_product(
    product_id: int, payload: ProductUpdate, user: SellerUser, db: Db
) -> ProductOut:
    """Partial edit of one of the seller's own products.

    Only the fields sent are changed; ``404`` for a product the seller
    doesn't own (enumeration guard).
    """
    return await MarketplaceService(db).update_product(user, product_id, payload)


@router.delete("/shop/products/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product(product_id: int, user: SellerUser, db: Db) -> None:
    """Remove one of the seller's own products. ``204`` on success; ``404``
    for a product the seller doesn't own."""
    await MarketplaceService(db).delete_product(user, product_id)


@router.post("/shop/image", response_model=ListingImagesOut)
async def upload_shop_image(
    user: SellerUser,
    db: Db,
    kind: str = Query("logo", pattern="^(logo|banner)$", description="logo | banner"),
    file: UploadFile = File(description="Shop logo or banner image"),
) -> ListingImagesOut:
    """Upload the shop's logo or banner and return a storage URL (M4, Task 4).

    The seller drops the returned URL into the shop profile's ``logo_url`` /
    ``banner_url`` via PATCH ``/shop/me``.
    """
    url = await MarketplaceService(db).upload_shop_image(user, file, kind)
    return ListingImagesOut(urls=[url])


@router.get("/products", response_model=ProductPageOut)
async def browse_products(
    user: CurrentUser,
    db: Db,
    q: str | None = Query(
        None,
        max_length=200,
        description="Search term over name/brand/description/manufacturer",
    ),
    category: str | None = Query(None, max_length=30, description="Filter: product category"),
    organic: bool | None = Query(None, description="Filter: only organic inputs"),
    availability: str | None = Query(None, max_length=20, description="Filter: availability"),
    min_price: float | None = Query(None, ge=0, description="Filter: minimum price per unit"),
    max_price: float | None = Query(None, ge=0, description="Filter: maximum price per unit"),
    brand: str | None = Query(None, max_length=120, description="Filter: brand substring"),
    sort: str = Query(SORT_NEWEST, pattern="|".join(SORT_KEYS), description="Sort order"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE, description="Items per page"),
) -> ProductPageOut:
    """Browse the public product market (paginated), filtered by category /
    organic / availability / price range / brand and sorted newest / oldest /
    by price. Passing ``q`` searches at the same time (M4, Task 4)."""
    return await MarketplaceService(db).browse_products(
        q=q,
        category=category,
        organic=organic,
        availability=availability,
        min_price=min_price,
        max_price=max_price,
        brand=brand,
        sort=sort,
        page=page,
        page_size=page_size,
    )


@router.get("/products/{product_id}", response_model=ProductDetailOut)
async def get_product(product_id: int, user: CurrentUser, db: Db) -> ProductDetailOut:
    """One product with its shop attached (public detail view, M4, Task 4).
    ``404`` when the product doesn't exist."""
    return await MarketplaceService(db).product_detail(product_id)


@router.get("/cart", response_model=CartOut)
async def get_cart(user: CurrentUser, db: Db) -> CartOut:
    return await MarketplaceService(db).get_cart(user)


@router.post("/cart/items", response_model=CartOut)
async def add_cart_item(
    payload: CartItemIn, user: CurrentUser, db: Db
) -> CartOut:
    return await MarketplaceService(db).add_to_cart(user, payload)


@router.delete("/cart/items/{item_id}", response_model=CartOut)
async def remove_cart_item(
    item_id: int, user: CurrentUser, db: Db
) -> CartOut:
    return await MarketplaceService(db).remove_from_cart(user, item_id)


@router.post("/checkout", response_model=OrderOut, status_code=201)
async def checkout(
    payload: CheckoutIn, user: CurrentUser, db: Db
) -> OrderOut:
    return await MarketplaceService(db).checkout(user, payload)


@router.get("/orders", response_model=list[OrderOut])
async def get_orders(user: CurrentUser, db: Db) -> list[OrderOut]:
    return await MarketplaceService(db).get_orders(user)
