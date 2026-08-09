"""Marketplace favourites schemas (M4, Task 6).

Request/response DTOs for the saved-items layer. ``add`` is idempotent (a
second POST for the same item returns the existing row) and the exactly-one
``listing_id`` / ``product_id`` rule is a business rule enforced in the service
(same as messaging's create context). Each favourite payload embeds the full
``CropListingOut`` / ``ProductOut`` so the favourites page renders the exact
same cards as the browse grids without a second fetch per row.
"""

from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.marketplace import CropListingOut, ProductOut


class FavoriteCreate(BaseModel):
    """POST /marketplace/favorites — save a crop listing or a product.

    Exactly one of ``listing_id`` / ``product_id`` must be provided (enforced
    in the service, matching messaging's conversation-context rule). Adding an
    item that is already saved is a no-op that returns the existing row.
    """

    listing_id: int | None = Field(default=None, gt=0)
    product_id: int | None = Field(default=None, gt=0)


class FavoriteOut(BaseModel):
    """One saved item with the listing or product attached (not both)."""

    id: int
    created_at: datetime
    listing: CropListingOut | None = None
    product: ProductOut | None = None


class FavoriteStatusOut(BaseModel):
    """Button state for a single item — is it saved, and by which row id.

    ``favorite_id`` lets the client remove the exact row (DELETE
    /marketplace/favorites/{id}) without first listing the whole collection.
    """

    favorited: bool
    favorite_id: int | None = None
    listing_id: int | None = None
    product_id: int | None = None
