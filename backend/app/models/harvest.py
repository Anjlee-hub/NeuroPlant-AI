"""Farmer-recorded actual harvests used as yield-estimation evidence."""

from datetime import date

from sqlalchemy import CheckConstraint, Date, Float, ForeignKey, Index, Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base
from app.models.base import TimestampMixin


class HarvestRecord(Base, TimestampMixin):
    __tablename__ = "harvest_records"
    __table_args__ = (
        CheckConstraint("actual_yield_kg > 0", name="ck_harvest_yield_positive"),
        CheckConstraint("area_hectares > 0", name="ck_harvest_area_positive"),
        Index("ix_harvest_user_schedule", "user_id", "schedule_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    schedule_id: Mapped[int] = mapped_column(
        ForeignKey("crop_schedules.id", ondelete="CASCADE"), index=True, nullable=False
    )
    actual_yield_kg: Mapped[float] = mapped_column(Float, nullable=False)
    area_hectares: Mapped[float] = mapped_column(Float, nullable=False)
    harvested_on: Mapped[date] = mapped_column(Date, nullable=False)
