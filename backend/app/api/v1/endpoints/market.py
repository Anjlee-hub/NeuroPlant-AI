"""Attributable crop-offer price comparisons."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.market import MarketPricePageOut
from app.services.market_intelligence import MarketIntelligenceService

router = APIRouter(prefix="/market", tags=["market"])

Db = Annotated[AsyncSession, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]


@router.get("/prices", response_model=MarketPricePageOut)
async def crop_prices(
    _user: CurrentUser,
    db: Db,
    crop_name: Annotated[str, Query(min_length=1, max_length=120)],
    location: Annotated[str | None, Query(min_length=1, max_length=200)] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> MarketPricePageOut:
    """Compare currently available farmer offers; these are not official mandi quotes."""
    return await MarketIntelligenceService(db).prices(
        crop_name,
        location=location,
        page=page,
        page_size=page_size,
    )
