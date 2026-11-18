"""Verified-source government scheme catalog and farmer usage events."""

from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base
from app.models.base import TimestampMixin


class GovernmentScheme(Base, TimestampMixin):
    __tablename__ = "government_schemes"
    __table_args__ = (Index("ix_government_schemes_active_verified", "is_active", "is_verified"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    category: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    benefits: Mapped[str | None] = mapped_column(Text, nullable=True)
    state_codes: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    crops: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    farmer_categories: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    eligibility_requirements: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    eligibility_rules: Mapped[dict[str, list[str]]] = mapped_column(
        JSON, default=dict, nullable=False
    )
    required_documents: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    application_instructions: Mapped[str | None] = mapped_column(Text, nullable=True)
    official_application_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    subsidy_details: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_name: Mapped[str] = mapped_column(String(200), nullable=False)
    source_url: Mapped[str] = mapped_column(String(1000), nullable=False)
    last_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class SchemeUsageEvent(Base):
    __tablename__ = "scheme_usage_events"
    __table_args__ = (
        Index("ix_scheme_usage_user_created", "user_id", "created_at"),
        Index("ix_scheme_usage_scheme_action", "scheme_id", "action"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    scheme_id: Mapped[int] = mapped_column(
        ForeignKey("government_schemes.id", ondelete="CASCADE"), index=True, nullable=False
    )
    action: Mapped[str] = mapped_column(String(30), nullable=False)
    state_code: Mapped[str | None] = mapped_column(String(8), nullable=True)
    crop_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
