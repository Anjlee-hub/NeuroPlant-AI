# M3 Task 5 Completion Report — Smart Crop Calendar & Reminder System

**Milestone:** M3 · **Task:** 5 · **Status:** Implemented — awaiting approval
**Branch:** `main` · **Date:** 2026-08-06

---

## 1. Overview

Task 5 delivers the **Smart Crop Calendar & Reminder System** — a per-farmer
planning surface that turns every catalog crop with a growth-stage template
into a live calendar. Each scheduled crop gets a **growth-stage timeline**
(planting → germination → vegetative → flowering → fruiting → harvest), a
stage- and disease-aware stream of **smart reminders** (watering, fertilizer,
organic/chemical treatments, disease monitoring, soil inspection), and a
**Farmer Calendar dashboard** that buckets the day's work into
today / upcoming / overdue / completed. Farmers can **complete, snooze, or
delete** tasks and add their own **custom notes / to-dos**.

The engine is fully **disease-aware**: when a scheduled crop has an active
scan with a predicted disease, the calendar replaces the generic organic /
monitoring rows with a tailored **"Monitor for &lt;Disease&gt;"** task plus
chemical-treatment and soil-plan reminders, all sourced from the existing
**Treatment engine (T1)**, **Soil engine (T3)**, and **Recovery tracker (T4)**
— reusing their services, never duplicating policy.

Everything else is built on the project's documented **policy-as-constants**
philosophy: interval heuristics live as module constants, crop stage durations
are **data-driven from the seeded catalog** (12 crops, `v1`), and `CalendarTask.scan_id`
provides a clean **push-notification seam** for the next milestone. The calendar
buckets are computed server-side from UTC dates, so the dashboard is consistent
across devices and timezones.

## 2. Features Implemented

### 2.1 Backend

**`app/models/calendar.py`** — four models:

- `CropCalendarCatalog` — the versioned catalog (exactly-one-active pattern,
  `CropCatalogVersion` shared with M2 catalog versions); `v1` seeded.
- `CropCalendarPlan` — per-crop growth template: `germination_days`,
  `vegetative_days`, `flowering_days`, `fruiting_days`, `harvest_days` with a
  `growth_days` property (sum of the five), unique per `(catalog_id, crop_id)`.
- `CropSchedule` — one per `(user_id, crop_id)`; stores the farmer's
  `planting_date`.
- `CalendarTask` — the reminder row: kind, title, `due_at`, `completed_at`,
  `snooze_count`, notes. **`scan_id` FK `ON DELETE SET NULL` is the
  push-notification seam** — the next milestone can target exactly the task
  that triggered a notification.

**`app/db/calendar_seed_data.py`** — `CALENDAR_PLANS` for **12 crops** keyed by
common name (Tomato, Potato, Wheat, Rice, Cotton, Soybean, Groundnut, Maize,
Chilli, Onion, Brinjal, Cabbage). Each plan's five stage durations are curated
so `growth_days` equals the crop's documented growth cycle (verified: e.g.
Tomato `8+22+15+22+8 = 75`; Cotton `10+40+30+55+25 = 160`).

**`app/services/calendar.py`** — `CalendarService` with documented policy
constants (`WATERING_INTERVAL_DAYS=7`, `ORGANIC_INTERVAL_DAYS=14`,
`SOIL_CHECK_INTERVAL_DAYS=30`, disease-monitor intervals that **tighten with
risk**: `high 3d / medium 5d / low 7d`, treatment-resume cadence per recovery
trend, etc.). It computes the six **contiguous stage ranges** from `planting_date`,
generates the recurring reminder stream, and adapts it to active scans:

| Method | Purpose |
|---|---|
| `crops()` | Catalog crops that have a growth template (crop picker) |
| `schedule(user, crop_id, planting_date?, regenerate?)` | Start/refresh a schedule, re-seeding its tasks |
| `dashboard(user)` | All schedules + bucket counts (today/upcoming/overdue/completed) |
| `add_custom_task` / `update_task` / `delete_task` | Task lifecycle (complete / snooze / re-title / re-date / note / delete) |

**Disease-aware adaptation** reuses `RecoveryTrackerService(db).tracker(scan)`
for risk/status, `RecommendationService(db).for_disease(...)` for remedy /
chemical titles, and `SoilRecommendationService(db).for_disease(...)` for soil
hints — all **best-effort** (`try/except`): a crop with no active scan simply
gets the generic organic/monitoring schedule.

**`app/api/v1/endpoints/calendar.py`** — router at `/api/v1/calendar`:

| Method | Path | Purpose |
|---|---|---|
| GET | `/calendar/crops` | Crops with growth templates (picker) |
| POST | `/calendar/crops/{crop_id}/schedule` | Start (or refresh) a schedule (201) |
| GET | `/calendar` | Farmer Calendar dashboard (schedules + bucket counts) |
| POST | `/calendar/tasks` | Add a custom note / to-do (201) |
| PATCH | `/calendar/tasks/{task_id}` | Complete / snooze / edit a task |
| DELETE | `/calendar/tasks/{task_id}` | Remove a task (204) |

**`alembic/versions/e4f6a8b0c2d1_add_crop_calendar.py`** — creates the four
tables + indexes (unique per catalog-crop and per user-crop, scan FK, due-date
index); applied to the dev DB. **`app/db/seed.py`** now runs
`seed_crop_calendar` in the standard version-swap (idempotent) seeder.

### 2.2 Frontend

- **`src/components/calendar/bucket-summary.tsx`** — the dashboard's four stat
  cards (overdue / today / upcoming / completed) with per-bucket accents,
  rendered straight from server counts.
- **`src/components/calendar/calendar-crop-picker.tsx`** — "Schedule a crop"
  card: pick any template crop (optional planting-date override), POST the
  schedule, then refetch the dashboard.
- **`src/components/calendar/schedule-card.tsx`** — one card per scheduled crop:
  crop name + planting date, an accessible progress bar
  (`role="progressbar"` / `aria-valuenow`), a horizontally scrollable
  **stage timeline**, tasks grouped into the four buckets (client-side
  `bucketTask` mirrors the server rule exactly), and per-task
  **complete / snooze / delete** actions (inline delete confirmation) plus an
  inline **custom note / to-do** form. Every mutation invalidates
  `["farmer-calendar"]` so the dashboard reflects the change immediately.
- **`src/pages/farmer-calendar.tsx`** — `FarmerCalendarPage`: auth gate,
  dashboard query, bucket summary, crop picker, schedule list; loading skeleton
  and error + retry states.
- **Routing / nav / i18n** — new `/calendar` route and a header nav item
  (`CalendarDays`); new `calendar` namespace in `en.json` / `hi.json`
  (UI chrome fully localized; catalog content stays English).

### 2.3 Future-Ready Architecture

- **Push notifications** — `CalendarTask.scan_id` (the scan that motivated a
  reminder) is the exact seam a future notifier targets; bucket/date logic is
  already server-side.
- **Weather / GPS** — all interval heuristics are isolated constants, so
  weather- or location-aware cadences plug in without schema changes.
- **Recurring schedules** — `regenerate=true` on `POST /crops/{id}/schedule`
  re-seeds a plan (e.g. for a new planting season) and is idempotent.

## 3. Test Results

### 3.1 Backend (`tests/test_calendar.py` — 15 new tests)
Catalog auth + templates (12 plans; stage sums match `growth_days`), schedule
happy path (6 contiguous stages, tomato harvest = planting + 74, all reminder
kinds), default wheat planting date, idempotent schedule + regenerate, 404 for
crops without a plan, dashboard bucket counts + progress, snooze / edit /
custom-task lifecycle, custom-task validation (422), cross-user 404s, auth
required, and the **disease overlay** (severe Early Blight → "Monitor for Early
Blight" with `scan_id`, tailored chemical + soil rows) and **recovery-history**
adaptation (improving log → next monitor due later).

**Full backend suite:** `279 passed, 1 skipped` (was 264/1) · coverage **84%**.
Ruff: **All checks passed**. MyPy: **Success (70 files)**.

### 3.2 Frontend (2 new test files, 13 tests)
- **`schedule-card.test.tsx` (8)** — `bucketTask` unit rules (completed-first,
  then today/overdue/upcoming), crop name + progress + stage timeline render,
  four bucket groups with counts, empty-task state, complete / snooze /
  delete-with-confirmation / add-custom-note actions hitting the API with the
  right payloads.
- **`farmer-calendar.test.tsx` (5)** — auth gate, bucket summary + scheduled
  crop render, empty state, error + retry, schedule-a-crop picker flow.

**Full frontend suite: `106 passed` (20 files)** (was 93/18).
TypeScript `tsc -b --noEmit`: **clean**. ESLint `--max-warnings=0`: **clean**.
Production `vite build`: **OK** (pre-existing chunk-size warning only).

## 4. Files Changed / Added

- **Backend (new):** `app/models/calendar.py`, `app/schemas/calendar.py`,
  `app/services/calendar.py`, `app/api/v1/endpoints/calendar.py`,
  `app/db/calendar_seed_data.py`,
  `alembic/versions/e4f6a8b0c2d1_add_crop_calendar.py`, `tests/test_calendar.py`
- **Backend (modified):** `app/models/__init__.py`, `app/api/v1/router.py`,
  `app/db/seed.py`, `app/main.py`
- **Frontend (new):** `src/types/calendar.ts`,
  `src/components/calendar/bucket-summary.tsx`,
  `src/components/calendar/calendar-crop-picker.tsx`,
  `src/components/calendar/schedule-card.tsx`, `src/pages/farmer-calendar.tsx`,
  and their 2 test files
- **Frontend (modified):** `src/lib/api.ts`, `src/app/router.tsx`,
  `src/components/layout/header.tsx`, `src/locales/en.json`, `src/locales/hi.json`

## 5. Future-Ready Notes

- **Notifications** — the scan_id seam + server-side bucketing mean a scheduler
  only needs to read due tasks and fire; no schema or API change required.
- **Recurring/adaptive cadence** — all intervals are constants; weather- or
  GPS-driven overrides replace the constants, not the model.
- **Regeneration** — re-seeding a schedule for a new season is a first-class
  API call and drops stale custom to-dos safely.
- **Restart the dev backend** to pick up the new `/calendar` routes (started
  without `--reload`).

**Next:** M3 Task 6 — awaiting user approval; do not begin unprompted.
