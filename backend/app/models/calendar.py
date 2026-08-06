"""Smart crop calendar & reminder system (M3, Task 5).

A versioned **crop calendar catalog** (planting window + per-stage durations,
following the treatment/soil catalog pattern) feeds a per-farmer, per-crop
**schedule** whose rows are concrete **reminder tasks**. The farmer schedules a
crop once; the service expands the crop's plan into growth-stage windows and a
task list (watering, fertilizer, organic/chemical treatment, disease
monitoring, soil inspection) that adapts to the crop's active diseases, their
recovery status and treatment history. Tasks are mutable rows (complete /
snooze / notes), so the calendar is the single source of truth for the Farmer
Calendar dashboard.

``CropSchedule`` + ``CalendarTask`` are *user-owned* (unlike the versioned
catalogs, which are global knowledge). ``CalendarTask.scan_id`` optionally links
a disease-monitoring / treatment reminder to the scan it came from — that link is
also the seam a future push-notification milestone uses to point the farmer
straight at the affected scan.
"""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.models.base import TimestampMixin
from app.models.catalog import Crop
from app.models.scan import Scan


class CropCalendarCatalog(Base, TimestampMixin):
    __tablename__ = "crop_calendar_catalogs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    version: Mapped[str] = mapped_column(String(32), unique=True, index=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    plans: Mapped[list[CropCalendarPlan]] = relationship(
        back_populates="catalog", cascade="all, delete-orphan"
    )


class CropCalendarPlan(Base, TimestampMixin):
    """Growth-stage template for one crop in the active catalog.

    ``planting_start_month`` / ``planting_end_month`` define the recommended
    sowing window (1–12, wrapping when start > end). The five stage durations
    (days) sum to the crop's days-to-maturity, so a planting date plus this
    plan yields every stage's date range deterministically.
    """

    __tablename__ = "crop_calendar_plans"
    __table_args__ = (UniqueConstraint("catalog_id", "crop_id", name="uq_crop_calendar_crop"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    catalog_id: Mapped[int] = mapped_column(
        ForeignKey("crop_calendar_catalogs.id", ondelete="CASCADE"), index=True, nullable=False
    )
    crop_id: Mapped[int] = mapped_column(
        ForeignKey("crops.id", ondelete="CASCADE"), index=True, nullable=False
    )

    planting_start_month: Mapped[int] = mapped_column(Integer, nullable=False)
    planting_end_month: Mapped[int] = mapped_column(Integer, nullable=False)
    germination_days: Mapped[int] = mapped_column(Integer, nullable=False)
    vegetative_days: Mapped[int] = mapped_column(Integer, nullable=False)
    flowering_days: Mapped[int] = mapped_column(Integer, nullable=False)
    fruiting_days: Mapped[int] = mapped_column(Integer, nullable=False)
    harvest_days: Mapped[int] = mapped_column(Integer, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    catalog: Mapped[CropCalendarCatalog] = relationship(back_populates="plans")
    crop: Mapped[Crop] = relationship()


class CropSchedule(Base, TimestampMixin):
    """A farmer's active schedule for one crop (planting-date anchored)."""

    __tablename__ = "crop_schedules"
    __table_args__ = (UniqueConstraint("user_id", "crop_id", name="uq_crop_schedule_user_crop"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    crop_id: Mapped[int] = mapped_column(
        ForeignKey("crops.id", ondelete="CASCADE"), index=True, nullable=False
    )
    planting_date: Mapped[date] = mapped_column(Date, nullable=False)

    crop: Mapped[Crop] = relationship()
    tasks: Mapped[list[CalendarTask]] = relationship(
        back_populates="schedule",
        cascade="all, delete-orphan",
        order_by="CalendarTask.due_at",
    )


class CalendarTask(Base, TimestampMixin):
    """One concrete reminder / task in a crop schedule.

    ``kind`` is the vocabulary enum (watering | fertilizer | organic_treatment |
    chemical_treatment | disease_monitoring | soil_inspection | custom). Generated
    tasks carry an English ``title`` (catalog content); ``custom`` tasks carry a
    farmer-typed title. ``snooze_count`` tracks how many times the task was
    snoozed (each snooze advances ``due_at``). ``completed_at`` moves the task to
    the Completed bucket; an unset one leaves it active (today / upcoming /
    overdue, computed from ``due_at``).
    """

    __tablename__ = "calendar_tasks"
    __table_args__ = (
        # The dashboard always buckets tasks per schedule in due order.
        # (schedule_id, due_at) is the natural access path.
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    schedule_id: Mapped[int] = mapped_column(
        ForeignKey("crop_schedules.id", ondelete="CASCADE"), index=True, nullable=False
    )
    # Disease-linked reminders point at the scan they came from (push seam).
    scan_id: Mapped[int | None] = mapped_column(
        ForeignKey("scans.id", ondelete="SET NULL"), index=True, nullable=True
    )
    kind: Mapped[str] = mapped_column(String(30), index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True, nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    snooze_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    schedule: Mapped[CropSchedule] = relationship(back_populates="tasks")
    scan: Mapped[Scan | None] = relationship()
