"""Smart crop calendar schemas (M3, Task 5).

The calendar is the farmer's per-crop planning surface: ``CalendarCropOut``
describes the catalog's growth-stage template (so the UI can show the planting
window and let the farmer pick a crop), ``CropCalendarOut`` is one scheduled
crop (planting date + computed stage ranges + its tasks + completion progress),
and ``FarmerCalendarOut`` aggregates every scheduled crop into the dashboard.
Tasks are mutable rows; ``CalendarTaskUpdate`` covers complete / snooze / notes /
due-date edits and ``CustomTaskIn`` creates a farmer-typed note task.

The growth stages and task kinds are vocabularies (module-level tuples) that
agree with the service's computed policy in ``app.services.calendar``.
"""

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

# Growth stages rendered by the crop calendar (ascending, seed -> harvest).
GROWTH_STAGES = ("planting", "germination", "vegetative", "flowering", "fruiting", "harvest")

# Reminder / task kinds the calendar can hold.
CALENDAR_TASK_KINDS = (
    "watering",
    "fertilizer",
    "organic_treatment",
    "chemical_treatment",
    "disease_monitoring",
    "soil_inspection",
    "custom",
)

# Dashboard buckets a task falls into.
CALENDAR_TASK_BUCKETS = ("today", "upcoming", "overdue", "completed")


class CalendarCropOut(BaseModel):
    """A crop with its growth-stage template (for the crop picker)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    common_name: str | None = None
    growth_days: int | None = None
    water_needs: str | None = None
    fertilizer_needs: str | None = None
    planting_start_month: int
    planting_end_month: int
    # Stage durations (days); they sum to ``growth_days``.
    germination_days: int
    vegetative_days: int
    flowering_days: int
    fruiting_days: int
    harvest_days: int
    notes: str | None = None


class ScheduleIn(BaseModel):
    """POST /calendar/crops/{crop_id}/schedule — start (or refresh) a schedule."""

    planting_date: date | None = Field(
        default=None,
        description="When the crop was/will be sown. Defaults to today if inside the "
        "planting window, otherwise the start of the next window.",
    )
    regenerate: bool = Field(
        default=False,
        description="Drop existing tasks and regenerate them (false = idempotent no-op "
        "when a schedule already exists).",
    )


class CalendarTaskOut(BaseModel):
    """One reminder / task."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    schedule_id: int
    scan_id: int | None = None
    kind: str
    title: str
    due_at: datetime
    completed_at: datetime | None = None
    snooze_count: int = 0
    notes: str | None = None


class CalendarTaskUpdate(BaseModel):
    """PATCH /calendar/tasks/{task_id} — partial edit (exclude-unset semantics).

    ``snooze_days`` advances ``due_at`` by the given number of days and bumps
    ``snooze_count``; ``completed`` toggles completion; ``notes`` / ``title`` /
    ``due_at`` edit the task directly. Exactly one field is expected per call.
    """

    completed: bool | None = None
    snooze_days: int | None = Field(default=None, ge=1, le=30)
    due_at: datetime | None = None
    title: str | None = Field(default=None, min_length=1, max_length=300)
    notes: str | None = Field(default=None, max_length=2000)


class CustomTaskIn(BaseModel):
    """POST /calendar/tasks — a farmer-typed note / to-do on a schedule."""

    schedule_id: int
    title: str = Field(min_length=1, max_length=300)
    due_at: datetime | None = None
    notes: str | None = Field(default=None, max_length=2000)


class CropStageOut(BaseModel):
    """One growth stage with its computed date range."""

    model_config = ConfigDict(from_attributes=True)

    stage: str
    start_date: date
    end_date: date


class CropCalendarOut(BaseModel):
    """One scheduled crop: planting date, stage ranges, tasks, progress."""

    model_config = ConfigDict(from_attributes=True)

    schedule_id: int
    crop_id: int
    crop_name: str
    common_name: str | None = None
    planting_date: date
    stages: list[CropStageOut]
    tasks: list[CalendarTaskOut]
    completed: int
    total: int
    progress: float


class FarmerCalendarOut(BaseModel):
    """The Farmer Calendar dashboard: every scheduled crop + bucket counts."""

    schedules: list[CropCalendarOut]
    today_count: int
    upcoming_count: int
    overdue_count: int
    completed_count: int
