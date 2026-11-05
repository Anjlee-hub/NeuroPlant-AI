"""Government scheme catalog and eligibility API schemas."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, model_validator


class GovernmentSchemeCreate(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    category: str = Field(min_length=2, max_length=80)
    description: str = Field(min_length=1, max_length=10000)
    benefits: str | None = Field(default=None, max_length=5000)
    state_codes: list[str] = Field(default_factory=list, max_length=40)
    crops: list[str] = Field(default_factory=list, max_length=100)
    farmer_categories: list[str] = Field(default_factory=list, max_length=40)
    eligibility_requirements: list[str] = Field(default_factory=list, max_length=100)
    eligibility_rules: dict[str, list[str]] = Field(default_factory=dict)
    required_documents: list[str] = Field(default_factory=list, max_length=100)
    application_instructions: str | None = Field(default=None, max_length=10000)
    official_application_url: HttpUrl | None = None
    subsidy_details: str | None = Field(default=None, max_length=5000)
    source_name: str = Field(min_length=2, max_length=200)
    source_url: HttpUrl
    last_verified_at: datetime | None = None
    is_verified: bool = False

    @model_validator(mode="after")
    def verified_records_require_verification_date(self) -> "GovernmentSchemeCreate":
        if self.is_verified and self.last_verified_at is None:
            raise ValueError("verified records require last_verified_at")
        return self


class GovernmentSchemeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    category: str
    description: str
    benefits: str | None
    state_codes: list[str]
    crops: list[str]
    farmer_categories: list[str]
    eligibility_requirements: list[str]
    required_documents: list[str]
    application_instructions: str | None
    official_application_url: str | None
    subsidy_details: str | None
    source_name: str
    source_url: str
    last_verified_at: datetime | None
    is_verified: bool


class GovernmentSchemePageOut(BaseModel):
    items: list[GovernmentSchemeOut]
    total: int
    page: int
    page_size: int
    pages: int
    source_status: Literal["scheme_records_available", "no_scheme_records"]
    source_note: str


class EligibilityCheckIn(BaseModel):
    state_code: str | None = Field(default=None, min_length=2, max_length=8)
    crop_name: str | None = Field(default=None, min_length=1, max_length=120)
    farmer_category: str | None = Field(default=None, min_length=1, max_length=80)


class EligibilityCheckOut(BaseModel):
    scheme_id: int
    outcome: Literal["potentially_eligible", "not_eligible", "unknown"]
    matched_rules: list[str]
    unmet_rules: list[str]
    explanation: str
    legal_determination: Literal[False] = False
