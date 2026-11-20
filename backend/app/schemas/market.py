"""Market intelligence schemas backed by farmer marketplace offers."""

from datetime import datetime

from pydantic import BaseModel, Field


class MarketOfferOut(BaseModel):
    listing_id: int
    crop_name: str
    variety: str | None
    quantity: float
    unit: str
    price_per_unit: float
    location: str | None
    source: str
    observed_at: datetime


class MarketComparisonOut(BaseModel):
    location: str | None
    unit: str
    offer_count: int
    minimum_price: float
    average_price: float
    maximum_price: float


class MarketPricePageOut(BaseModel):
    crop_name: str
    items: list[MarketOfferOut] = Field(default_factory=list)
    comparisons: list[MarketComparisonOut] = Field(default_factory=list)
    total: int
    page: int
    page_size: int
    pages: int
    source: str = "farmer-marketplace-listings"
    current_offer_note: str
    last_updated_at: datetime | None
    historical_trend_available: bool = False
    historical_trend_note: str = (
        "No historical market-price observations are stored; "
        "current offers are not a price history."
    )
