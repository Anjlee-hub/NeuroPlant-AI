"""Market-price provider interface and marketplace-offer adapter.

Farmer marketplace asking prices are not represented as official market/mandi
prices. The adapter exposes them as offers with explicit source and timestamps;
it never invents or implies a historical trend.
"""

from __future__ import annotations

from typing import Protocol

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.marketplace import CropListing
from app.schemas.market import (
    MarketComparisonOut,
    MarketOfferOut,
    MarketPricePageOut,
)


class MarketPriceProvider(Protocol):
    """Data source contract for normalized, attributable crop-price offers."""

    async def search(
        self,
        crop_name: str,
        *,
        location: str | None,
        page: int,
        page_size: int,
    ) -> MarketPricePageOut: ...


class MarketplaceOfferProvider:
    """Read currently available farmer offers from the existing marketplace."""

    source = "farmer-marketplace-listings"

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def search(
        self,
        crop_name: str,
        *,
        location: str | None,
        page: int,
        page_size: int,
    ) -> MarketPricePageOut:
        predicates = [
            func.lower(CropListing.crop_name) == crop_name.strip().lower(),
            CropListing.availability.in_(("available", "limited")),
        ]
        if location:
            predicates.append(CropListing.location.ilike(f"%{location.strip()}%"))

        base = select(CropListing).where(*predicates)
        total = int(
            await self.db.scalar(
                select(func.count()).select_from(
                    select(CropListing.id).where(*predicates).subquery()
                )
            )
            or 0
        )
        rows = await self.db.scalars(
            base.order_by(CropListing.created_at.desc(), CropListing.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        comparisons = await self.db.execute(
            select(
                CropListing.location,
                CropListing.unit,
                func.count(CropListing.id),
                func.min(CropListing.price),
                func.avg(CropListing.price),
                func.max(CropListing.price),
            )
            .where(*predicates)
            .group_by(CropListing.location, CropListing.unit)
            .order_by(CropListing.location, CropListing.unit)
        )
        last_updated = await self.db.scalar(
            select(func.max(CropListing.updated_at)).where(*predicates)
        )

        return MarketPricePageOut(
            crop_name=crop_name.strip(),
            items=[
                MarketOfferOut(
                    listing_id=row.id,
                    crop_name=row.crop_name,
                    variety=row.variety,
                    quantity=row.quantity,
                    unit=row.unit,
                    price_per_unit=row.price,
                    location=row.location,
                    source=self.source,
                    observed_at=row.updated_at,
                )
                for row in rows
            ],
            comparisons=[
                MarketComparisonOut(
                    location=location_name,
                    unit=unit,
                    offer_count=int(count),
                    minimum_price=float(minimum),
                    average_price=float(average),
                    maximum_price=float(maximum),
                )
                for location_name, unit, count, minimum, average, maximum in comparisons
            ],
            total=total,
            page=page,
            page_size=page_size,
            pages=(total + page_size - 1) // page_size if total else 0,
            current_offer_note=(
                "Current farmer marketplace asking offers; these are not official mandi prices."
                if total
                else "No currently available farmer offers match this query."
            ),
            last_updated_at=last_updated,
        )


class MarketIntelligenceService:
    """Application service over a pluggable price provider."""

    def __init__(
        self,
        db: AsyncSession,
        provider: MarketPriceProvider | None = None,
    ) -> None:
        self.provider = provider or MarketplaceOfferProvider(db)

    async def prices(
        self,
        crop_name: str,
        *,
        location: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> MarketPricePageOut:
        return await self.provider.search(
            crop_name,
            location=location,
            page=page,
            page_size=page_size,
        )
