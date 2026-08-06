# Milestone 3 Completion Report — Smart Treatment, Soil, Crop Doctor, Calendar & Voice AI

**Milestone:** M3 · **Tag:** `v0.3.0-m3` · **Date:** 2026-08-06
**Branch:** `main` · **Status:** ✅ Complete

---

## 1. Milestone Summary

Milestone 3 turned NeuroPlant AI from a scan-and-detect platform into a
**complete crop-care product**: every detected disease now carries a curated
treatment plan and a soil-care plan, each scan opens a full **Crop Doctor
dashboard** with a recovery tracker and a printable PDF report, farmers get a
**smart crop calendar** with growth-stage reminders, and a bilingual
**voice AI assistant** answers questions in English and हिन्दी — by text or
by voice. Offline-first and i18n continue to hold: every new surface reuses
the existing scan pipeline, storage, auth, and en/hi localization.

The work spanned **six task groups** (M3 Task 1 → Task 6) plus a final
verification pass:

| Task | Scope | Delivered |
|---|---|---|
| M3 T1 | Treatment recommendation engine | Versioned data-driven catalog, 26 curated plans, `RecommendationService` (for_disease / for_scan), endpoints, migration |
| M3 T2 | Treatment UI | `RecommendationsPanel`/`View` (12 expandable sections), i18n en/hi, print-friendly care plans |
| M3 T3 | Soil recommendation engine | Versioned soil catalog, 26 curated soil plans, `SoilContext` seam, computed soil-health score, endpoints |
| M3 T4 | Crop Doctor dashboard | Per-scan dashboard (plant overview + AI diagnosis + treatment/soil reused) + **Recovery Tracker** (logs, %, status, risk) + printable PDF report |
| M3 T5 | Smart crop calendar | 4 models, 12-crop growth templates, stage ranges + recurring reminders, disease-aware overlay, `GET/POST /calendar` |
| M3 T6 | Voice AI assistant | Rule-based bilingual `AssistantService` + `POST /assistant`, 3 framework-free speech services, assistant page + SpeakButton everywhere |

Every gate is green: **295 backend tests** (1 skipped, **82% coverage**), **143
frontend tests** (26 files), clean Ruff/MyPy/ESLint/TypeScript, a successful
production build with PWA artifacts, a verified OpenAPI 3.1 spec (**37 paths,
42 operations**), a single Alembic head with the dev DB current, and a live
**24/24 end-to-end smoke journey** walking the whole product in one script
(`backend/scripts/m3_smoke_journey.py`).

## 2. Architecture Overview

```
┌────────────────────────── Frontend (React 19 / Vite 6 / TS) ────────────────────────────┐
│  Pages       home · login · register · scan-crop · scan-history · scan-detail ·          │
│              scan-doctor · farmer-calendar · assistant · offline-queue · profile          │
│  M3 surfaces RecommendationsPanel/View · SoilRecommendationsPanel/View · RecoveryTracker  │
│              · plant-overview · ai-diagnosis · schedule-card · calendar-crop-picker ·     │
│              AssistantPage · SpeakButton · SpeechInput                                   │
│  Speech      SpeechRecognitionService · SpeechSynthesisService · VoiceAssistantService   │
│              (framework-free; speechLocale en-IN/hi-IN, one row per language)             │
│  State       zustand (auth, sync-ui) · TanStack React Query (server cache)                │
│  i18n        en / hi — 564 keys each, full parity (no missing/empty values)               │
│  Offline     IndexedDB syncQueue + completedQueue + kv · PWA service worker               │
│  API         typed client (lib/api.ts) → bearer token, single-flight refresh              │
└───────────────────────────────────────┬───────────────────────────────────────────────────┘
                                         │  HTTPS / JSON
┌───────────────────────────────────────┴──────────────────── Backend (FastAPI / SQLAlchemy2) ─┐
│  Routers      auth · users · catalog · scans (+sync) · recommendations · soil · recovery ·   │
│               calendar · assistant · health                                                  │
│  Engine       RecommendationService · SoilRecommendationService · RecoveryTrackerService ·   │
│               CalendarService · AssistantService — all reuse the M2 scan pipeline + storage   │
│  Data         Versioned catalogs (Recommendation / Soil) with exactly-one-active guard;      │
│               curated seed plans keyed by (crop, disease); idempotent seeders by version      │
│  DB           SQLite (dev) / Postgres (prod) via Alembic · 7 revisions total, 4 added in M3   │
│  Security     Reused M1 auth (argon2, TOTP, OTP, sessions/devices, rate limiting)            │
└───────────────────────────────────────────────────────────────────────────────────────────────┘
```

**Design principles carried through M3:**

- **Data-driven, versioned policy.** Treatment and soil content live in
  database catalogs with an exactly-one-active guard and idempotent,
  version-keyed seeders — no hard-coded advice in service code. 26 curated
  plans each, keyed by `(crop common_name, disease)`, with crops disambiguated
  (tomato and potato both have Late Blight).
- **One scan pipeline, reused.** Treatment, soil, recovery, calendar and
  assistant all read the *same* scan/disease data written by the M2 pipeline —
  no duplicated policy.
- **Consistency + honest content.** The Crop Doctor reuses the T1–T3 panels
  unchanged; the soil-health score (0–5) is computed from a seeded base rating
  adjusted for severity and confidence, with a documented `SoilContext` seam
  for future weather/location/soil-test inputs. No fake translations are ever
  shipped — the voice layer ships real en + hi and is structured so 12 Indian
  languages can be added as real locale packs in M4.
- **Best-effort degradation.** Every assistant engine call is try/except
  best-effort, so a missing scan or catalog degrades to a helpful fallback
  instead of an error.

## 3. Features Completed

### 3.1 Treatment recommendation engine (T1)
- `RecommendationCatalog` (exactly one active) + `DiseaseRecommendation` (one
  plan per catalog/disease), nested item schemas
  (`HomemadeRemedyOut`/`OrganicRemedyOut`/`ChemicalRecommendationOut`) and a
  self-contained `DiseaseRecommendationOut`.
- **26 curated plans** in `app/db/recommendation_seed_data.py`, seeder merges
  curated content with existing `Disease`-row fields as fallback.
- `RecommendationService.for_disease / for_scan` (by-id-then-by-name);
  ownership-guarded `GET /scans/{id}/recommendations`; 404 no-plan / 503
  unseeded responses.

### 3.2 Treatment recommendation UI (T2)
- `RecommendationsPanel` + `RecommendationsView` with **12 expandable
  sections** (homemade / organic / chemical remedies, fertilizer, watering,
  sunlight, temperature, humidity, prevention, recovery, isolation,
  monitoring), rendered in Scan Crop (live) and Scan Detail (history).
- Full en/hi i18n under the `treatment` namespace; print-friendly CSS.

### 3.3 Soil recommendation engine (T3)
- `SoilRecommendationCatalog` + `SoilRecommendation` (one plan per
  catalog/disease); `SoilRecommendationService` with the future-ready
  `SoilContext` seam (weather/location/soil-test plug in later).
- **Computed soil-health score (0–5)** from seeded base rating, adjusted for
  severity and low confidence.
- **26 curated soil plans** (`app/db/soil_seed_data.py`, `SOIL_BY_CROP`),
  disease- and severity-aware; endpoints `GET /soil/catalog`,
  `GET /soil/diseases/{id}?severity&confidence`,
  `GET /scans/{id}/soil-recommendations`.

### 3.4 Crop Doctor dashboard + recovery tracker (T4)
- Per-scan page consolidating **Plant Overview** (crop/part/disease/confidence/
  severity/risk/scan date/model), **AI Diagnosis** (explanation,
  what-AI-observed, Grad-CAM heatmap, top-5), and the **treatment + soil
  panels reused unchanged** from T1–T3.
- New **Crop Recovery Tracker**: farmer logs treatment / date / progress notes;
  recovery % / status / risk computed from documented policy constants;
  reminders seam documented.
- **Printable PDF report** via `window.print()` + print-only header +
  `print:hidden` chrome (offline/PWA-friendly; no server-side PDF generator).
- Backend `RecoveryLog` model + `RecoveryTrackerService` +
  ownership-guarded `GET/POST/PATCH/DELETE /scans/{id}/recovery(/logs)`.

### 3.5 Smart crop calendar & reminders (T5)
- 4 models (`CropCalendarCatalog` / `CropCalendarPlan` / `CropSchedule` /
  `CalendarTask` with a `scan_id` push seam), **12-crop growth templates** in
  `app/db/calendar_seed_data.py`.
- `CalendarService`: stage ranges + recurring reminders, disease-aware overlay
  reusing the T1/T3/T4 services best-effort.
- `GET /calendar` (dashboard: schedules + bucket counts),
  `GET /calendar/crops`, `POST /calendar/crops/{id}/schedule`,
  `POST/PATCH/DELETE /calendar/tasks`.
- Farmer-calendar page with `schedule-card`, `bucket-summary`, and
  `calendar-crop-picker` components.

### 3.6 Voice AI assistant & multilingual voice (T6)
- Backend `AssistantService`: bilingual **keyword intent routing** (treatment →
  fertilizer → soil → calendar → recovery → disease → greeting → help),
  **Devanagari → हिन्दी auto-detection**, replies in the language asked in,
  reusing Scan/Recommendation/Soil/Recovery/Calendar services best-effort.
- Frontend **3 framework-free speech services** (`SpeechRecognitionService`,
  `SpeechSynthesisService`, `VoiceAssistantService`) with
  `speechLocale` en-IN/hi-IN (one row per language — the M4 growth point for
  all 12 Indian languages).
- **Assistant page** (text+voice in, voice out, intent badge, chips, clear,
  typing/error/empty, auth gate) + **SpeakButton "read it aloud"** integrated
  into every major panel (treatment, soil, recovery, plant overview, AI
  diagnosis, calendar schedule-card). Unsupported browsers render nothing —
  no dead controls.

## 4. Backend APIs (OpenAPI 3.1, 37 paths · 42 operations)

| Area | Path | Methods |
|---|---|---|
| Auth | `/api/v1/auth/register` · `/login` · `/logout` · `/me` | POST / POST / POST / GET |
| OTP / MFA | `/api/v1/auth/otp/send` · `/otp/verify` | POST |
|  | `/api/v1/auth/mfa/setup` · `/mfa/confirm` · `/mfa/verify` · `/mfa/backup-codes` | POST |
| Sessions / devices | `/api/v1/auth/refresh` · `/auth/sessions` · `/auth/devices` · `/auth/devices/{id}` | POST / GET / GET / DELETE |
| Scans | `/api/v1/scans` | GET (list/filter/sort) · POST (upload) |
| Scan sync | `/api/v1/scans/sync` | POST (offline batch) |
| Scan detail / explain | `/api/v1/scans/{id}` · `/scans/{id}/explain` | GET · DELETE / GET |
| Treatment (M3) | `/api/v1/recommendations/catalog` · `/recommendations/diseases/{id}` · `/scans/{id}/recommendations` | GET |
| Soil (M3) | `/api/v1/soil/catalog` · `/soil/diseases/{id}` · `/scans/{id}/soil-recommendations` | GET |
| Recovery (M3) | `/api/v1/scans/{id}/recovery` · `/recovery/logs` · `/recovery/logs/{log_id}` | GET / POST / PATCH · DELETE |
| Calendar (M3) | `/api/v1/calendar` · `/calendar/crops` · `/calendar/crops/{id}/schedule` | GET / GET / POST |
|  | `/api/v1/calendar/tasks` · `/calendar/tasks/{id}` | POST / PATCH · DELETE |
| Assistant (M3) | `/api/v1/assistant` | POST |
| Catalog / Users | `/api/v1/catalog/crops` · `/api/v1/users/me` | GET / GET · PATCH |
| Health | `/health` · `/ready` | GET |

**M3 added 15 paths / 17 operations** on top of the M2 surface (22 paths /
25 operations). Key M3 schemas verified present in the live spec:
`DiseaseRecommendationOut`, `SoilRecommendationOut`, `RecoveryTrackerOut`,
`RecoveryLogOut`, `FarmerCalendarOut`, `CropCalendarOut`, `CalendarTaskOut`,
`AssistantReplyOut`.

## 5. Frontend Pages

| Route | Page | M3 role |
|---|---|---|
| `/` | `home.tsx` | Landing / dashboard |
| `/login` `/register` `/login/mfa` `/settings/mfa` | auth | Reused M1 |
| `/detect` | `scan-crop.tsx` | **Live Scan Crop** — upload/camera/crop/part → `POST /scans` → result with top-5 + heatmap + explanation + treatment + soil |
| `/scans` | `scan-history.tsx` | History grid (filters/sort/pagination, badges) |
| `/scans/:scanId` | `scan-detail.tsx` | Full report + gallery + AI diagnosis + treatment + soil panels |
| `/scans/:scanId/doctor` | `scan-doctor.tsx` | **Crop Doctor dashboard** — plant overview + AI diagnosis + treatment + soil + recovery tracker + **printable PDF report** |
| `/doctor` | → `/scans` | Nav hub redirect (live per-scan dashboards) |
| `/calendar` | `farmer-calendar.tsx` | **Smart crop calendar** — bucket summary + schedule cards + reminders + crop picker |
| `/assistant` | `assistant.tsx` | **Voice AI assistant** — text/voice in, spoken replies, intent badge, chips |
| `/offline` | `offline-queue.tsx` | Sync queue + progress + completed (M2) |
| `/profile` | `profile.tsx` | Profile + edit name (M2.1) |
| `/marketplace` | `coming-soon.tsx` | Honest "planned for Milestone 6" |

All M3 pages reuse the shared design system (status badges, state cards,
skeletons, reduced-motion, dark mode). SpeakButton is a self-hiding control on
unsupported browsers; the assistant conversation guards against missing
`scrollTo` in embedded webviews.

## 6. Voice Architecture

```
User (en | hi) ─▶ SpeechInput (recognition) ─▶ AssistantPage ─▶ POST /assistant
                                                       │            │
        ┌──────────┐   flatten via describe.ts ◀───────┘            ▼
        │ SpeakButton ◀─ every panel            AssistantService.answer(user, query, lang)
        └──────────┘                              ├─ language detect (Devanagari → hi)
                                                  ├─ keyword intent routing
                                                  └─ reuses Scan / Recommendation / Soil /
                                                     Recovery / Calendar services (best-effort)
```

- **Engine is rule-based (no LLM), backend-owned.** Intents: `disease`,
  `treatment`, `fertilizer`, `soil`, `recovery`, `calendar`, `greeting`,
  `help`, `fallback`. Reply carries its own `lang`, so the frontend reads it
  aloud in the language it was answered in.
- **Three framework-free services** share one speech seam
  (`VoiceAssistantService`); `speechLocale(lang)` is a single row per language
  → voice locale (`en → en-IN`, `hi → hi-IN`), the documented M4 growth point.
- **Multilingual without fakes.** en + hi ship real; recognition normalizes
  vendor errors to codes the UI localizes.

## 7. Soil Engine

- Versioned `SoilRecommendationCatalog` + one `SoilRecommendation` per
  (catalog, disease); 26 curated plans (`SOIL_BY_CROP`) covering the 12 crops /
  26 diseases.
- **Soil-health score (0–5)**: seeded base rating per disease, adjusted for
  scan severity and low confidence; returned alongside soil care,
  suitability, water, fertilizer, pH, and prevention sections.
- `SoilContext` dataclass is the documented seam where weather / location /
  soil-test inputs plug in later — the service already consumes it, the
  endpoints just don't feed it yet.

## 8. Calendar

- 12-crop growth templates (tomato, potato, rice, wheat, maize, cotton,
  sugarcane, onion, chili, brinjal, okra, cabbage) with stage ranges and
  recurring task patterns.
- `CalendarService` generates tasks from `planting_date`, buckets them into
  today / upcoming / overdue, and overlays disease-aware reminders by reusing
  the T1/T3/T4 services best-effort when a scan is attached (`scan_id` push
  seam for future notifications).
- API + UI: pick a crop → schedule → dashboard with bucket summaries,
  complete / snooze / edit / delete tasks, add custom to-dos.

## 9. Crop Doctor

- `/scans/:scanId/doctor` consolidates the whole M3 story for one scan:
  **Plant Overview** → **AI Diagnosis** (explanation + heatmap + top-5) →
  **Treatment** → **Soil** → **Recovery tracker**.
- Recovery: log treatment + date + progress; computed **recovery % / status /
  risk** from documented constants; full CRUD via ownership-guarded endpoints.
- **PDF export** is a client-side print flow (`window.print()` + print-only
  header + `print:hidden` chrome) — works offline and in the PWA.

## 10. Test Summary

| Suite | Result |
|---|---|
| Backend `pytest` (full) | **295 collected · 294 passed · 1 skipped · 82% coverage** (3542 stmts, 654 missed) |
| — M3 feature tests | **75** (recommendations 13 · soil 18 · recovery 14 · calendar 15 · assistant 15) |
| `ruff check .` | clean (incl. new `scripts/m3_smoke_journey.py`) |
| `ruff format --check .` | own M3 files formatted (pre-existing deviations scoped out) |
| `mypy app` | clean (73 source files) |
| Frontend `vitest` | **143 passed** (26 files) |
| Frontend `tsc -b --noEmit` | clean |
| Frontend ESLint (`--max-warnings=0`) | clean |
| Frontend `vite build` | ✅ success (~9.8 s), PWA generated (pre-existing chunk/CSS warnings only) |
| Live smoke journey | **24 / 24 passed** (`backend/scripts/m3_smoke_journey.py`, live backend :8001) |

### Backend M3 feature files

| Feature | File | Tests |
|---|---|---|
| Treatment engine | `test_recommendations.py` | 13 |
| Soil engine | `test_soil_recommendations.py` | 18 |
| Recovery tracker | `test_recovery.py` | 14 |
| Calendar | `test_calendar.py` | 15 |
| Assistant | `test_assistant.py` | 15 |

### Frontend M3 coverage (of the 143 tests / 26 files)

Soil recommendations 9 · recovery tracker 8 · schedule-card 8 · farmer-calendar
5 · speech-recognition 7 · speech-synthesis 7 · voice-assistant 7 ·
speak-button 5 · speech-input 5 · assistant page 6 · scan-crop 4 · scan-detail
9 · scan-doctor 4 · profile 4 (+ offline-queue 13, scan-history 7, ai-diagnosis
5, plant-overview 4, status-badges 6, scan-sync 4).

## 11. Coverage

**Overall backend: 82%** (no `--cov-fail-under` configured; informational).
Strong modules: scan_pipeline 94%, scans service 96%, explain 97%, detection
93%, preprocess 97%, config 97%, seed 84%, soil service 80%, recovery service
66%, calendar service 58%. The new assistant service sits at **41%** — its
bilingual copy/composition branches and best-effort fallbacks are covered by
the 15 behavior tests but not exhaustively unit-tested; the final
verification's live smoke journey exercised the en + hi paths end-to-end.

## 12. Known Limitations

1. **Real ML model not wired** — the classifier adapter slot is still a
   deterministic mock; real weights + validation are M4 work.
2. **Assistant is rule-based, en/hi only** — no LLM, no other languages yet;
   the architecture is ready for 12 Indian languages (real locale packs +
   one `speechLocale` row each, no fakes).
3. **PDF export is print-based** (client-side) — no server-rendered PDF; quality
   depends on the browser's print engine.
4. **Weather / location / soil-test inputs** are designed for (the `SoilContext`
   seam) but not yet fed — soil scores currently derive from scan data only.
5. **Single JS chunk** (~791 kB, 231 kB gzip) still triggers Vite's >500 kB
   warning; code-splitting deferred.
6. **SQLite dev DB** (Postgres via same Alembic migrations in production);
   **no Docker / Redis** — Celery runs eager, rate limiter is in-process.
7. **No live browser QA** — `NODE_ENV=production` is global here, so
   visual/dark-mode/responsive verification is token/class-level automated
   rather than on-device.

## 13. Future Work (M4)

- **12 Indian languages** — real `locales/<code>.json` packs + `speechLocale`
  rows; voice adapts automatically because replies carry their own `lang`.
- **Real ML detection** — load weights into `classifiers.py` adapters,
  validate on the target crop set, keep the rule-baseline as fallback.
- **Push notifications** — the calendar buckets and recovery reminders already
  have a documented seam (`scan_id`, server-side buckets) for a notifier.
- **LLM-assisted assistant** — swap/upgrade the rule router behind the same
  `POST /assistant` contract; add weather-aware answers feeding `SoilContext`.
- **PWA hardening** — code-splitting, chunk budget, background sync.
- **Expert workflows** — review/verify queues, expert annotations, community Q&A.
- **Postgres + Docker in dev** — lift the SQLite fallback once available.

---

**Milestone 3 is complete and tagged `v0.3.0-m3`. Milestone 4 has not begun.**
