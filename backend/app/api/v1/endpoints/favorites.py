"""Marketplace favourites endpoints (M4, Task 6).

Four routes under ``/marketplace/favorites`` power the saved-items layer:

* **GET** ``""`` — the caller's saved items, newest first.
* **GET** ``/status`` — is one listing/product saved (button state).
* **POST** ``""`` — save a listing or product (idempotent).
* **DELETE** ``/{id}`` — remove one of the caller's saved items (idempotent).

Every route requires an authenticated user; exactly-one target + existence are
``400`` (matching messaging's create context) and row ownership answers ``404``
(the platform's enumeration guard). ``/status`` is declared before any
``/{favorite_id}`` route so FastAPI never reads it as an id.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.favorites import FavoriteCreate, FavoriteOut, FavoriteStatusOut
from app.services.favorites import FavoritesService

router = APIRouter(prefix="/marketplace/favorites", tags=["marketplace"])

Db = Annotated[AsyncSession, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]


@router.get("", response_model=list[FavoriteOut])
async def list_favorites(user: CurrentUser, db: Db) -> list[FavoriteOut]:
    """The caller's saved items, newest first, each with the full listing or
    product attached (the page renders the same cards as the browse grids)."""
    return await FavoritesService(db).list(user)


@router.get("/status", response_model=FavoriteStatusOut)
async def favorite_status(
    user: CurrentUser,
    db: Db,
    listing_id: int | None = Query(None, gt=0, description="Target crop listing"),
    product_id: int | None = Query(None, gt=0, description="Target product"),
) -> FavoriteStatusOut:
    """Whether the caller has saved the given listing or product, plus the row
    id to remove. Exactly one target must be provided."""
    return await FavoritesService(db).status(user, listing_id=listing_id, product_id=product_id)


@router.post("", response_model=FavoriteOut, status_code=status.HTTP_201_CREATED)
async def add_favorite(payload: FavoriteCreate, user: CurrentUser, db: Db) -> FavoriteOut:
    """Save a listing or product (idempotent — saving an already-saved item
    returns the existing row). Exactly one target must be provided."""
    return await FavoritesService(db).add(user, payload)


@router.delete("/{favorite_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_favorite(favorite_id: int, user: CurrentUser, db: Db) -> None:
    """Remove one of the caller's saved items. ``204`` on success; ``404`` for
    a row the caller doesn't own (enumeration guard)."""
    await FavoritesService(db).remove(user, favorite_id)
