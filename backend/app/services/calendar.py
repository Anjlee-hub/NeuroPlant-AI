"""Smart crop calendar & reminder service (M3, Task 5).

Turns a crop's growth-stage template into a farmer's concrete schedule: given a
planting date, every stage gets a date range, and the plan expands into reminder
tasks (watering, fertilizer, organic/chemical treatment, disease monitoring,
soil inspection). When the farmer has scans for the crop, the schedule **adapts
to the active diseases**: monitoring tightens, treatment reminders are retitled
with the actual remedy from the treatment/soil engines, and the first treatment
follows the latest recovery log (treatment history). All of it is *computed
policy* — documented constants below — over catalog + farmer-recorded content,
never hardcoded per-crop/per-disease in controllers.

Future-ready seams: ``_crop_scans`` + ``CalendarTask.scan_id`` already link
every disease reminder to its scan (a push-notification milestone just reads
those rows); the planting-window logic in ``crops()``/``_default_planting_date``
is where a GPS- or weather-based recommendation would slot in (a future
``CalendarContext`` alongside ``SoilContext``); nothing in this schema changes.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, time, timedelta

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.logging import get_logger
from app.models.calendar import (
    CalendarTask,
    CropCalendarCatalog,
    CropCalendarPlan,
    CropSchedule,
)
from app.models.catalog import Crop
from app.models.scan import Scan
from app.models.user import User
from app.schemas.calendar import (
    CALENDAR_TASK_BUCKETS,
    CalendarCropOut,
    CalendarTaskOut,
    CalendarTaskUpdate,
    CropCalendarOut,
    CropStageOut,
    CustomTaskIn,
    FarmerCalendarOut,
)
from app.services.recommendations import (
    CatalogUnavailableError,
    RecommendationNotFoundError,
    RecommendationService,
)
from app.services.recovery import RecoveryTrackerService
from app.services.soil import (
    SoilCatalogUnavailableError,
    SoilNotFoundError,
    SoilRecommendationService,
)

logger = get_logger(__name__)


class CalendarPlanNotFoundError(Exception):
    """No active crop-calendar plan for the requested crop."""


class CalendarScheduleNotFoundError(Exception):
    """The crop schedule doesn't exist or belongs to another user."""


class CalendarTaskNotFoundError(Exception):
    """The calendar task doesn't exist or belongs to another user."""


# ── Calendar policy ─────────────────────────────────────────────────────────
# Computed, documented heuristics. Base cadence applies to every crop; disease
# overlay tightens/re-titles tasks while a diagnosis is active.

# Watering cadence across the whole crop window.
WATERING_INTERVAL_DAYS = 7

# Base organic crop-protection cadence during the vegetative->fruiting window.
ORGANIC_INTERVAL_DAYS = 14

# Soil checks: at sowing, then every 30 days through the crop window.
SOIL_CHECK_INTERVAL_DAYS = 30

# Base pest/disease monitoring cadence while no diagnosis is active.
BASE_MONITOR_INTERVAL_DAYS = 7

# Active-diagnosis monitoring cadence, tightened by the scan's risk level.
DISEASE_MONITOR_INTERVAL_DAYS: dict[str, int] = {"high": 3, "medium": 5, "low": 7}

# Active-diagnosis treatment cadences.
ORGANIC_ACTIVE_INTERVAL_DAYS = 7
CHEMICAL_ACTIVE_INTERVAL_DAYS = 5

# Chemical treatments are only surfaced for high-risk / severe cases; organic
# reminders cover the rest (matches the recovery/soil risk philosophy).
CHEMICAL_RISK_LEVELS = ("high",)
CHEMICAL_SEVERITY_LEVELS = ("severe",)

# After the latest treatment log, the next treatment resumes after this many
# days based on the farmer-reported crop response (treatment-history signal).
TREATMENT_RESUME_DAYS: dict[str, int] = {
    "worsening": 3,
    "no-change": 5,
    "improving": 7,
    "recovered": 0,
}


class CalendarService:
    """Owns the crop-calendar catalog reads and per-farmer schedule/tasks."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ── Catalog reads ──────────────────────────────────────────────────────

    async def crops(self) -> list[CalendarCropOut]:
        """Every crop with a growth-stage template in the active catalog."""
        plans = await self.db.scalars(
            select(CropCalendarPlan)
            .join(CropCalendarCatalog)
            .where(CropCalendarCatalog.is_active.is_(True))
            .options(selectinload(CropCalendarPlan.crop))
            .order_by(CropCalendarPlan.crop_id)
        )
        return [self._crop_out(plan) for plan in plans]

    # ── Schedule + task management ─────────────────────────────────────────

    async def schedule(
        self,
        user: User,
        crop_id: int,
        planting_date: date | None = None,
        *,
        regenerate: bool = False,
        now: datetime | None = None,
    ) -> CropCalendarOut:
        """Create (or refresh) the farmer's schedule for one crop.

        Idempotent by default: a schedule that already exists is returned
        unchanged. ``regenerate=True`` rebuilds the task list from the current
        policy + diagnoses (used after the recovery picture changes).
        """
        now = now or _now()
        today = now.date()
        plan = await self._active_plan(crop_id)
        planting = planting_date or self._default_planting_date(plan, today)

        schedule = await self.db.scalar(
            select(CropSchedule)
            .where(CropSchedule.user_id == user.id, CropSchedule.crop_id == crop_id)
            .options(selectinload(CropSchedule.crop))
        )
        if schedule is None:
            schedule = CropSchedule(user_id=user.id, crop_id=crop_id, planting_date=planting)
            self.db.add(schedule)
            await self.db.flush()
        elif not regenerate:
            return await self._calendar_out(schedule, now)

        schedule.planting_date = planting
        await self.db.execute(delete(CalendarTask).where(CalendarTask.schedule_id == schedule.id))
        scans = await self._crop_scans(user.id, crop_id)
        tasks = await self._generate_tasks(
            schedule.id,
            plan,
            crop=plan.crop,
            planting_date=planting,
            today=today,
            scans=scans,
        )
        self.db.add_all(tasks)
        await self.db.commit()
        return await self._calendar_out(schedule, now)

    async def dashboard(self, user: User, now: datetime | None = None) -> FarmerCalendarOut:
        """The full Farmer Calendar: every scheduled crop + bucket counts."""
        now = now or _now()
        today = now.date()
        schedules = await self.db.scalars(
            select(CropSchedule)
            .where(CropSchedule.user_id == user.id)
            .options(
                selectinload(CropSchedule.crop),
                selectinload(CropSchedule.tasks),
            )
            .order_by(CropSchedule.planting_date)
        )
        out: list[CropCalendarOut] = []
        counts = {f"{bucket}_count": 0 for bucket in CALENDAR_TASK_BUCKETS}
        for schedule in schedules:
            tasks = list(schedule.tasks)
            for task in tasks:
                counts[f"{self._bucket(task, today)}_count"] += 1
            plan = await self._active_plan(schedule.crop_id)
            completed = sum(1 for task in tasks if task.completed_at is not None)
            total = len(tasks)
            out.append(
                CropCalendarOut(
                    schedule_id=schedule.id,
                    crop_id=schedule.crop_id,
                    crop_name=schedule.crop.common_name or schedule.crop.name,
                    common_name=schedule.crop.common_name,
                    planting_date=schedule.planting_date,
                    stages=self._stages(plan, schedule.planting_date),
                    tasks=[CalendarTaskOut.model_validate(t) for t in tasks],
                    completed=completed,
                    total=total,
                    progress=round(completed / total, 3) if total else 0.0,
                )
            )
        return FarmerCalendarOut(schedules=out, **counts)

    async def add_custom_task(self, user: User, payload: CustomTaskIn) -> CalendarTaskOut:
        """Add a farmer-typed note / to-do to one of the user's schedules."""
        schedule = await self.db.scalar(
            select(CropSchedule).where(CropSchedule.id == payload.schedule_id)
        )
        if schedule is None or schedule.user_id != user.id:
            raise CalendarScheduleNotFoundError("No such schedule for this user")
        task = CalendarTask(
            schedule_id=payload.schedule_id,
            kind="custom",
            title=payload.title,
            due_at=payload.due_at or _now(),
            notes=payload.notes,
        )
        self.db.add(task)
        await self.db.commit()
        await self.db.refresh(task)
        return CalendarTaskOut.model_validate(task)

    async def update_task(
        self,
        user: User,
        task_id: int,
        payload: CalendarTaskUpdate,
        now: datetime | None = None,
    ) -> CalendarTaskOut:
        """Complete / snooze / re-title / re-date / note a task (partial)."""
        now = now or _now()
        task = await self._task_for_user(task_id, user.id)
        data = payload.model_dump(exclude_unset=True)
        if "snooze_days" in data:
            days = data.pop("snooze_days")
            task.due_at = task.due_at + timedelta(days=days)
            task.snooze_count = (task.snooze_count or 0) + 1
        if "completed" in data:
            task.completed_at = now if data.pop("completed") else None
        for key, value in data.items():
            setattr(task, key, value)
        await self.db.commit()
        await self.db.refresh(task)
        return CalendarTaskOut.model_validate(task)

    async def delete_task(self, user: User, task_id: int) -> None:
        """Remove a task from the user's schedule."""
        task = await self._task_for_user(task_id, user.id)
        await self.db.delete(task)
        await self.db.commit()

    # ── Task generation (base + disease-aware overlay) ────────────────────

    async def _generate_tasks(
        self,
        schedule_id: int,
        plan: CropCalendarPlan,
        *,
        crop: Crop,
        planting_date: date,
        today: date,
        scans: list[Scan],
    ) -> list[CalendarTask]:
        """Expand a plan into concrete CalendarTask rows.

        Base cadence spans the whole crop window; when a diagnosis is active,
        monitoring/treatment reminders are replaced by disease-specific ones
        that start from today and are retitled with the actual remedy.
        """
        stages = self._stage_offsets(plan)
        total = stages["harvest_start"] + plan.harvest_days
        harvest_end = planting_date + timedelta(days=total - 1)
        crop_label = crop.common_name or crop.name

        active_scans = [s for s in scans if s.disease_id is not None]
        has_disease = bool(active_scans)

        rows: list[dict] = self._base_rows(
            crop_label, planting_date, today, total, stages, has_disease
        )
        if has_disease:
            rows += await self._disease_rows(active_scans, today, harvest_end, crop_label)

        tasks: list[CalendarTask] = []
        for row in rows:
            due = row["due"]
            if due.date() > harvest_end or due.date() < planting_date:
                continue
            tasks.append(
                CalendarTask(
                    schedule_id=schedule_id,
                    kind=row["kind"],
                    title=row["title"],
                    due_at=due,
                    notes=row.get("notes"),
                    scan_id=row.get("scan_id"),
                )
            )
        return tasks

    def _base_rows(
        self,
        crop_label: str,
        planting_date: date,
        today: date,
        total: int,
        stages: dict[str, int],
        has_disease: bool,
    ) -> list[dict]:
        """Watering / fertilizer / soil / organic / monitoring cadence."""
        rows: list[dict] = []
        veg_start = stages["vegetative_start"]
        flow_start = stages["flowering_start"]
        fruit_start = stages["fruiting_start"]
        harvest_start = stages["harvest_start"]

        # Watering — weekly across the whole window.
        for day in range(0, total + 1, WATERING_INTERVAL_DAYS):
            rows.append(self._row("watering", f"Water the {crop_label}", planting_date, day))
        # Fertilizer — basal + at each reproductive stage boundary.
        for label, day in (
            ("basal", 0),
            ("top-dress", veg_start),
            ("flowering", flow_start),
            ("fruiting", fruit_start),
        ):
            rows.append(self._row("fertilizer", f"Apply {label} fertilizer", planting_date, day))
        # Soil checks — sowing + monthly.
        for day in range(0, total + 1, SOIL_CHECK_INTERVAL_DAYS):
            rows.append(self._row("soil_inspection", "Inspect soil health", planting_date, day))
        if has_disease:
            # Organic + monitoring are replaced by the disease overlay below.
            return rows
        # Organic crop protection — every 14 days during veg..fruiting.
        for day in range(veg_start, harvest_start + 1, ORGANIC_INTERVAL_DAYS):
            rows.append(
                self._row("organic_treatment", "Apply organic crop protection", planting_date, day)
            )
        # Base monitoring — weekly during veg..harvest.
        for day in range(veg_start, harvest_start + 1, BASE_MONITOR_INTERVAL_DAYS):
            rows.append(
                self._row(
                    "disease_monitoring",
                    "Monitor the crop for pests and disease",
                    planting_date,
                    day,
                )
            )
        return rows

    async def _disease_rows(
        self,
        scans: list[Scan],
        today: date,
        harvest_end: date,
        crop_label: str,
    ) -> list[dict]:
        """Tighten monitoring + add treatment reminders per active diagnosis."""
        rows: list[dict] = []
        window = max((harvest_end - today).days + 1, 0)
        if window <= 0:
            return rows
        remedy_cache: dict[int, str | None] = {}
        chemical_cache: dict[int, str | None] = {}
        soil_cache: dict[int, str | None] = {}

        for scan in scans:
            tracker = await RecoveryTrackerService(self.db).tracker(scan)
            if tracker.status == "recovered":
                continue
            disease_id = int(scan.disease_id or 0)
            risk = tracker.risk  # low | medium | high
            # Treatment history: resume from the latest log + its response offset.
            start_day = 0
            if tracker.timeline:
                last = tracker.timeline[-1]
                offset = TREATMENT_RESUME_DAYS.get(last.progress or "no-change", 5)
                resume = last.applied_at.date() + timedelta(days=offset)
                start_day = max(start_day, (resume - today).days)
            start_day = min(max(start_day, 0), window)

            # Monitoring — tight cadence per risk.
            monitor_int = DISEASE_MONITOR_INTERVAL_DAYS[risk]
            for day in range(start_day, window, monitor_int):
                rows.append(
                    self._row(
                        "disease_monitoring",
                        f"Monitor for {scan.disease_name}",
                        today,
                        day,
                        scan_id=scan.id,
                    )
                )
            # Organic treatment — retitled with the actual homemade remedy.
            remedy = remedy_cache.get(disease_id)
            if remedy is None:
                remedy = await self._remedy_title(disease_id)
                remedy_cache[disease_id] = remedy
            for day in range(start_day, window, ORGANIC_ACTIVE_INTERVAL_DAYS):
                rows.append(
                    self._row(
                        "organic_treatment",
                        f"Apply organic treatment: {remedy}",
                        today,
                        day,
                        scan_id=scan.id,
                    )
                )
            # Chemical treatment — only high-risk / severe cases.
            if risk in CHEMICAL_RISK_LEVELS or scan.severity in CHEMICAL_SEVERITY_LEVELS:
                chemical = chemical_cache.get(disease_id)
                if chemical is None:
                    chemical = await self._chemical_title(disease_id)
                    chemical_cache[disease_id] = chemical
                for day in range(start_day, window, CHEMICAL_ACTIVE_INTERVAL_DAYS):
                    rows.append(
                        self._row(
                            "chemical_treatment",
                            f"Apply chemical treatment: {chemical}",
                            today,
                            day,
                            scan_id=scan.id,
                        )
                    )
            # Soil inspection — once, with the soil plan's improvement note.
            suggestion = soil_cache.get(disease_id)
            if suggestion is None:
                suggestion = await self._soil_suggestion(disease_id)
                soil_cache[disease_id] = suggestion
            if suggestion:
                rows.append(
                    self._row(
                        "soil_inspection",
                        f"Improve soil health for the {crop_label}",
                        today,
                        0,
                        notes=suggestion,
                    )
                )
        return rows

    # ── Best-effort content from the recommendation engines ───────────────

    async def _remedy_title(self, disease_id: int) -> str:
        try:
            rec = await RecommendationService(self.db).for_disease(disease_id)
            if rec.homemade_remedies:
                return rec.homemade_remedies[0].title
        except (RecommendationNotFoundError, CatalogUnavailableError):
            pass
        return "a natural remedy"

    async def _chemical_title(self, disease_id: int) -> str:
        try:
            rec = await RecommendationService(self.db).for_disease(disease_id)
            if rec.chemical_recommendations:
                return rec.chemical_recommendations[0].product
        except (RecommendationNotFoundError, CatalogUnavailableError):
            pass
        return "the recommended chemical"

    async def _soil_suggestion(self, disease_id: int) -> str | None:
        try:
            soil = await SoilRecommendationService(self.db).for_disease(disease_id)
            if soil.improvement_suggestions:
                return soil.improvement_suggestions[0]
        except (SoilNotFoundError, SoilCatalogUnavailableError):
            pass
        return None

    # ── Helpers ────────────────────────────────────────────────────────────

    async def _active_plan(self, crop_id: int) -> CropCalendarPlan:
        plan = await self.db.scalar(
            select(CropCalendarPlan)
            .join(CropCalendarCatalog)
            .where(
                CropCalendarCatalog.is_active.is_(True),
                CropCalendarPlan.crop_id == crop_id,
            )
            .options(selectinload(CropCalendarPlan.crop))
        )
        if plan is None:
            raise CalendarPlanNotFoundError(f"No calendar plan available for crop {crop_id}")
        return plan

    async def _crop_scans(self, user_id: int, crop_id: int) -> list[Scan]:
        rows = await self.db.scalars(
            select(Scan)
            .where(
                Scan.user_id == user_id,
                Scan.crop_id == crop_id,
                Scan.deleted_at.is_(None),
            )
            .order_by(Scan.created_at.desc())
        )
        return list(rows)

    async def _task_for_user(self, task_id: int, user_id: int) -> CalendarTask:
        task = await self.db.scalar(
            select(CalendarTask)
            .join(CropSchedule)
            .where(
                CalendarTask.id == task_id,
                CropSchedule.user_id == user_id,
            )
        )
        if task is None:
            raise CalendarTaskNotFoundError("No such calendar task for this user")
        return task

    async def _calendar_out(self, schedule: CropSchedule, now: datetime) -> CropCalendarOut:
        plan = await self._active_plan(schedule.crop_id)
        crop = plan.crop  # loaded by _active_plan (avoids async lazy-load on schedule.crop)
        tasks = await self.db.scalars(
            select(CalendarTask)
            .where(CalendarTask.schedule_id == schedule.id)
            .order_by(CalendarTask.due_at)
        )
        task_list = [CalendarTaskOut.model_validate(t) for t in tasks]
        completed = sum(1 for t in task_list if t.completed_at is not None)
        total = len(task_list)
        return CropCalendarOut(
            schedule_id=schedule.id,
            crop_id=schedule.crop_id,
            crop_name=crop.common_name or crop.name,
            common_name=crop.common_name,
            planting_date=schedule.planting_date,
            stages=self._stages(plan, schedule.planting_date),
            tasks=task_list,
            completed=completed,
            total=total,
            progress=round(completed / total, 3) if total else 0.0,
        )

    def _crop_out(self, plan: CropCalendarPlan) -> CalendarCropOut:
        crop = plan.crop
        return CalendarCropOut(
            id=crop.id,
            name=crop.name,
            common_name=crop.common_name,
            growth_days=crop.growth_days,
            water_needs=crop.water_needs,
            fertilizer_needs=crop.fertilizer_needs,
            planting_start_month=plan.planting_start_month,
            planting_end_month=plan.planting_end_month,
            germination_days=plan.germination_days,
            vegetative_days=plan.vegetative_days,
            flowering_days=plan.flowering_days,
            fruiting_days=plan.fruiting_days,
            harvest_days=plan.harvest_days,
            notes=plan.notes,
        )

    @staticmethod
    def _stage_offsets(plan: CropCalendarPlan) -> dict[str, int]:
        """Start-day offset from sowing for each stage boundary."""
        veg = plan.germination_days
        flow = veg + plan.vegetative_days
        fruit = flow + plan.flowering_days
        harvest = fruit + plan.fruiting_days
        return {
            "vegetative_start": veg,
            "flowering_start": flow,
            "fruiting_start": fruit,
            "harvest_start": harvest,
        }

    @staticmethod
    def _stages(plan: CropCalendarPlan, planting_date: date) -> list[CropStageOut]:
        """Six growth stages (planting + five ranges) with date ranges."""
        stages: list[CropStageOut] = [
            CropStageOut(stage="planting", start_date=planting_date, end_date=planting_date)
        ]
        cursor = planting_date
        for stage in ("germination", "vegetative", "flowering", "fruiting", "harvest"):
            days = getattr(plan, f"{stage}_days")
            end = cursor + timedelta(days=days - 1)
            stages.append(CropStageOut(stage=stage, start_date=cursor, end_date=end))
            cursor = end + timedelta(days=1)
        return stages

    @staticmethod
    def _row(
        kind: str,
        title: str,
        anchor: date,
        day: int,
        *,
        scan_id: int | None = None,
        notes: str | None = None,
    ) -> dict:
        """Build a pending task row at ``anchor + day`` (midnight, naive UTC)."""
        return {
            "kind": kind,
            "title": title,
            "due": datetime.combine(anchor + timedelta(days=day), time.min),
            "scan_id": scan_id,
            "notes": notes,
        }

    @staticmethod
    def _bucket(task: CalendarTask, today: date) -> str:
        """Bucket a task: completed first, then today / overdue / upcoming."""
        if task.completed_at is not None:
            return "completed"
        due = task.due_at.date()
        if due == today:
            return "today"
        if due < today:
            return "overdue"
        return "upcoming"

    @staticmethod
    def _default_planting_date(plan: CropCalendarPlan, today: date) -> date:
        """Today when inside the sowing window, else the next window start."""
        month = today.month
        if _month_in_window(month, plan.planting_start_month, plan.planting_end_month):
            return today
        year = today.year
        if plan.planting_start_month < month:
            year += 1
        return date(year, plan.planting_start_month, 1)


def _month_in_window(month: int, start: int, end: int) -> bool:
    """Whether ``month`` falls in the [start, end] window (wraps new year)."""
    if start <= end:
        return start <= month <= end
    return month >= start or month <= end


def _now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)
