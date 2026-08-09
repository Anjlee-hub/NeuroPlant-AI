"""Marketplace reviews & reputation endpoints (M4, Task 6).

Five routes under ``/marketplace/reviews`` power the ratings & reviews layer:

* **GET** ``""`` — paginated reviews for one listing / product / seller, with
  the aggregate summary (and, for a single item, the caller's own review).
* **GET** ``/mine`` — every review the caller wrote (edit/delete surface).
* **POST** ``""`` — review a listing or product (``409`` on duplicate,
  ``400`` on self-review).
* **PATCH** ``/{id}`` — edit one of the caller's own reviews (``404`` for
  others').
* **DELETE** ``/{id}`` — remove one of the caller's own reviews (``404`` for
  others').

Every route requires an authenticated user — reviews are never anonymous. The
list endpoint needs exactly one of ``listing_id`` / ``product_id`` / ``seller_id``
(``400`` otherwise). ``/mine`` is declared before any ``/{review_id}`` route so
FastAPI never reads it as an id.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.reviews import (
    ReviewCreate,
    ReviewOut,
    ReviewPageOut,
    ReviewUpdate,
)
from app.services.reviews import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE, ReviewsService

router = APIRouter(prefix="/marketplace/reviews", tags=["marketplace"])

Db = Annotated[AsyncSession, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]


@router.get("", response_model=ReviewPageOut)
async def list_reviews(
    user: CurrentUser,
    db: Db,
    listing_id: int | None = Query(None, gt=0, description="Reviews of one listing"),
    product_id: int | None = Query(None, gt=0, description="Reviews of one product"),
    seller_id: int | None = Query(None, gt=0, description="A seller's reputation reviews"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE, description="Items per page"),
) -> ReviewPageOut:
    """Paginated reviews for one subject (listing / product / seller), newest
    first. Exactly one of the three filters must be provided. The response
    carries the aggregate ``summary`` and, for a single item, the caller's own
    ``my_review`` so the detail page knows whether to offer write/edit."""
    return await ReviewsService(db).list_reviews(
        user,
        listing_id=listing_id,
        product_id=product_id,
        seller_id=seller_id,
        page=page,
        page_size=page_size,
    )


@router.get("/mine", response_model=list[ReviewOut])
async def my_reviews(user: CurrentUser, db: Db) -> list[ReviewOut]:
    """Every review the caller wrote, newest first (manage/edit/delete)."""
    return await ReviewsService(db).mine(user)


@router.post("", response_model=ReviewOut, status_code=status.HTTP_201_CREATED)
async def create_review(payload: ReviewCreate, user: CurrentUser, db: Db) -> ReviewOut:
    """Review a listing or product. ``201`` on success, ``409`` when the caller
    has already reviewed this exact item, ``400`` on a self-review or a bad /
    unknown target. The reviewer is always the authenticated user."""
    return await ReviewsService(db).create(user, payload)


@router.patch("/{review_id}", response_model=ReviewOut)
async def update_review(
    review_id: int, payload: ReviewUpdate, user: CurrentUser, db: Db
) -> ReviewOut:
    """Edit one of the caller's own reviews (only sent fields change). ``404``
    for a review the caller didn't write (enumeration guard)."""
    return await ReviewsService(db).update(user, review_id, payload)


@router.delete("/{review_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_review(review_id: int, user: CurrentUser, db: Db) -> None:
    """Remove one of the caller's own reviews. ``204`` on success; ``404`` for
    a review the caller didn't write."""
    await ReviewsService(db).delete(user, review_id)
