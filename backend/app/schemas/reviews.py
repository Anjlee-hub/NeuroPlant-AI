"""Marketplace reviews schemas (M4, Task 6).

Request/response DTOs for the ratings & reviews layer. A review targets a crop
listing *or* a product (exactly one, service-enforced); ``seller_id`` on the
response is the derived subject (listing farmer / product shop owner) so a
seller reputation summary can be shown on the shop profile.

The rating scale (1–5), title and content bounds, and the whitespace-only guard
are validated here at the boundary — the ownership + dedup + self-review rules
live in ``app.services.reviews``.
"""

from datetime import datetime

from pydantic import BaseModel, Field, field_validator, model_validator

from app.schemas.messaging import ListingRefOut, ProductRefOut

# Rating scale + text bounds (mirrors app/models/marketplace_trust.py).
RATING_MIN = 1
RATING_MAX = 5
REVIEW_TITLE_MAX_LENGTH = 200
REVIEW_CONTENT_MAX_LENGTH = 2000


def _strip_non_blank(value: str) -> str:
    """Trim padding and reject a payload that is only whitespace.

    ``min_length`` counts raw characters, so a payload of spaces passes it; the
    blank-content guard is this validator's job. The trimmed value is what gets
    persisted.
    """
    stripped = value.strip()
    if not stripped:
        raise ValueError("content must not be blank")
    return stripped


class ReviewCreate(BaseModel):
    """POST /marketplace/reviews — one review of a listing or a product.

    Exactly one of ``listing_id`` / ``product_id`` must be provided (enforced in
    the service). Duplicate reviews for the same reviewer + target answer 409;
    reviewing your own item answers 400 (self-review).
    """

    listing_id: int | None = Field(default=None, gt=0)
    product_id: int | None = Field(default=None, gt=0)
    rating: int = Field(ge=RATING_MIN, le=RATING_MAX, description="Star rating 1–5")
    title: str | None = Field(default=None, max_length=REVIEW_TITLE_MAX_LENGTH)
    content: str = Field(min_length=1, max_length=REVIEW_CONTENT_MAX_LENGTH)

    @field_validator("content")
    @classmethod
    def _content(cls, value: str) -> str:
        return _strip_non_blank(value)

    @field_validator("title")
    @classmethod
    def _title(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None


class ReviewUpdate(BaseModel):
    """PATCH /marketplace/reviews/{id} — edit one of the caller's own reviews.

    Partial: only the fields sent are changed. At least one field must be sent
    (422 otherwise); a blank ``content`` is rejected.
    """

    rating: int | None = Field(default=None, ge=RATING_MIN, le=RATING_MAX)
    title: str | None = Field(default=None, max_length=REVIEW_TITLE_MAX_LENGTH)
    content: str | None = Field(default=None, min_length=1, max_length=REVIEW_CONTENT_MAX_LENGTH)

    @field_validator("content")
    @classmethod
    def _content(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return _strip_non_blank(value)

    @field_validator("title")
    @classmethod
    def _title(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None

    @model_validator(mode="after")
    def _at_least_one(self) -> "ReviewUpdate":
        if self.rating is None and self.title is None and self.content is None:
            raise ValueError("provide at least one of rating, title, content")
        return self


class RatingSummaryOut(BaseModel):
    """Aggregate rating for an item or a seller.

    ``average`` is 0.0 when there are no reviews; ``distribution`` maps each
    star value 5→1 to its count (present for every scale value, zero-filled).
    """

    average: float = Field(ge=0, le=float(RATING_MAX))
    total: int = Field(ge=0)
    distribution: dict[int, int] = Field(default_factory=dict)


class ReviewOut(BaseModel):
    """One review as returned by the API, with the reviewer's display name and
    the item it is about (``None`` when the item has since been deleted)."""

    id: int
    reviewer_id: int
    reviewer_name: str
    seller_id: int
    rating: int
    title: str | None
    content: str
    created_at: datetime
    updated_at: datetime
    listing: ListingRefOut | None = None
    product: ProductRefOut | None = None


class ReviewPageOut(BaseModel):
    """Paginated reviews for one target (listing / product) or one seller.

    ``summary`` is the rating aggregate for the filtered subject; ``my_review``
    is the caller's own review of the item (only populated when a single item
    — ``listing_id`` or ``product_id`` — is filtered), so the detail page knows
    whether to show "Write a review" or "Edit your review" without a second
    request.
    """

    items: list[ReviewOut] = Field(default_factory=list)
    total: int = Field(ge=0)
    page: int = Field(ge=1)
    page_size: int = Field(ge=1)
    pages: int = Field(ge=0)
    summary: RatingSummaryOut
    my_review: ReviewOut | None = None
