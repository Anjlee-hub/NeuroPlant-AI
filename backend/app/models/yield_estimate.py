"""Persisted yield-estimate requests for honest forecast/harvest comparisons."""

from datetime import date, datetime

from sqlalchemy import Date, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class YieldEstimateRecord(Base):
    __tablename__ = "yield_estimate_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    crop_id: Mapped[int] = mapped_column(
        ForeignKey("crops.id", ondelete="CASCADE"), index=True, nullable=False
    )
    schedule_id: Mapped[int | None] = mapped_column(
        ForeignKey("crop_schedules.id", ondelete="SET NULL"), index=True, nullable=True
    )
    planting_date: Mapped[date] = mapped_column(Date, nullable=False)
    area_hectares: Mapped[float] = mapped_column(Float, nullable=False)
    estimated_yield_kg: Mapped[float | None] = mapped_column(Float, nullable=True)
    historical_harvest_count: Mapped[int] = mapped_column(Integer, nullable=False)
    reliability: Mapped[str] = mapped_column(String(20), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
