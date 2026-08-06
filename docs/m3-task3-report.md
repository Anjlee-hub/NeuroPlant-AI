# M3 Task 3 Completion Report — Smart Soil Recommendation Engine

**Milestone:** M3 · **Task:** 3 · **Status:** Implemented — awaiting approval
**Branch:** `main` · **Date:** 2026-08-06

---

## 1. Overview

Task 3 extends the Treatment Recommendation Engine (M3 T1/T2) with **soil
intelligence** — a versioned, data-driven soil plan for every disease in the
knowledge catalog. Each plan covers **nine guidance areas** (recommended soil
type, pH range, moisture level, drainage, organic matter, NPK, micronutrients,
compost, mulching), a **crop-fit profile** (soil suitability + a computed
soil-health rating with improvement suggestions), and **disease-aware advice**
that adapts to the detected disease, crop, severity and confidence.

No treatment feature from Tasks 1–2 was modified; the soil module is additive —
its own models, catalog, service, endpoints, and frontend section. Content is
**not hardcoded anywhere in controllers**: every guidance area, disease note and
severity adjustment lives in the seeded catalog, and the API is a thin read-only
layer over the active version.

**Scale:** 12 crops · 26 diseases · 26 curated soil plans (one per disease),
each with a full nine-area profile plus disease/severity-aware content.

## 2. Features Implemented

### 2.1 ORM models (`app/models/soil.py`)
- **`SoilRecommendationCatalog`** — one row per catalog version (`version`
  unique, `is_active` boolean); activating a new version atomically deactivates
  the previous one (same pattern as the treatment catalog).
- **`SoilRecommendation`** — one complete soil plan per `(catalog_id,
  disease_id)` (unique constraint `uq_soil_catalog_disease`), storing:
  - the **nine guidance areas** (soil type, pH, moisture, drainage, organic
    matter, NPK, micronutrients as JSON list, compost, mulching);
  - the **soil-health profile** (`soil_suitability` sentence, `base_soil_health`
    rating, `improvement_suggestions` JSON list);
  - **disease-aware notes** (`disease_soil_notes`);
  - **severity-aware content** as JSON dicts keyed by severity
    (`severity_notes`, `severity_suggestions`).

### 2.2 Service (`app/services/soil.py`)
- **`SoilRecommendationService`** — read-only resolution against the active
  catalog: `catalog()`, `for_disease()`, `for_scan()` (by `disease_id` first,
  then by disease-name, exactly like the treatment engine).
- **`SoilContext`** — the explicit **future-ready seam**. Today it carries the
  signals a scan already knows (disease, crop, severity, confidence). Weather,
  location, and real soil-test data will be added as new optional context fields
  and flow through the same scoring pipeline **without changing the API**.
- **Soil-health score** — a 0–5 estimate computed from the crop's seeded base
  rating, then adjusted for disease severity and low detection confidence
  (documented policy constants `BASE_HEALTH_SCORE`, `SEVERITY_PENALTY`,
  `CONFIDENCE_LOW_THRESHOLD`). Labeled `poor | fair | good | excellent`, with a
  plain-language summary of what influenced the rating.
- **Errors** — `SoilNotFoundError` (404) and `SoilCatalogUnavailableError`
  (503), registered in `app/main.py` like the treatment errors.

### 2.3 Schemas (`app/schemas/soil.py`)
- **`SoilRecommendationOut`** — one self-contained payload: the nine areas, the
  computed `SoilHealthOut` (label + score + summary), suitability, improvement
  suggestions, and the disease/severity/confidence context the advice was
  adapted for (including a low-confidence note).
- **`SoilRecommendationCatalogOut`** — catalog metadata with plan count.
- Canonical `SOIL_SEVERITIES` (`low | moderate | severe`) and
  `SOIL_HEALTH_LEVELS` vocabularies so seeds, service and docs agree.

### 2.4 Seed data (`app/db/soil_seed_data.py`)
- **`SOIL_BY_CROP`** — a curated profile for all 12 crops (`SOIL_VERSION = "v1"`):
  the nine guidance areas, suitability sentence, base soil-health rating and
  improvement suggestions, plus per-disease soil notes and severity-aware
  notes/suggestions. Written for Indian field conditions (pH ranges, FYM/compost
  doses, mulching/drainage advice following state-agriculture extension
  literature).
- **Seeder** (`seed_soil_recommendations` in `app/db/seed.py`) — merges each
  crop profile with its disease notes into one row per catalog disease;
  idempotent and version-swapping like the treatment seeder.

### 2.5 API endpoints
| Method | Path | Purpose |
|---|---|---|
| GET | `/api/v1/soil/catalog` | Active soil catalog metadata (version, plan count) |
| GET | `/api/v1/soil/diseases/{disease_id}` | Full soil plan for one disease; optional `severity`/`confidence` query params to preview adaptive behaviour |
| GET | `/api/v1/scans/{scan_id}/soil-recommendations` | Soil plan for a scan's predicted disease, adapted to the scan's own severity + confidence (ownership-guarded) |

All are auth-gated; a scan without a curated soil plan returns **404**, and an
unseeded catalog returns **503** with a `python -m app.db.seed` hint.

### 2.6 Database migration
- `alembic/versions/c5e1f3a7b9d2_add_soil_recommendation_catalog.py` creates the
  two soil tables (head is now `c5e1f3a7b9d2`); applied to the dev DB and the
  seeder run (`26 soil plans`).

### 2.7 Frontend
- **`src/types/soil.ts`** — TS types mirroring `SoilRecommendationOut`.
- **`src/lib/api.ts`** — `api.getScanSoilRecommendations(scanId)` →
  `GET /scans/{id}/soil-recommendations` (auth-gated, same refresh/retry).
- **`src/components/treatment/soil-recommendations.tsx`** —
  **`SoilRecommendationsPanel`** (loading skeleton, empty state on 404, error
  with retry, success) + **`SoilRecommendationsView`**:
  - **Health header card** — localized Soil Health badge (Excellent/Good/Fair/
    Poor) with a 0–5 score bar and reason, soil suitability, improvement
    suggestions (baseline + severity-merged), a "how this disease affects your
    soil" box, severity notes, and an amber low-confidence warning.
  - **Nine expandable guidance cards** (accordion pattern, keyboard-accessible
    with `aria-expanded`/`aria-controls`), micronutrients rendered as chips.
- **Pages** — `scan-crop.tsx` and `scan-detail.tsx` render
  `<SoilRecommendationsPanel>` right below the existing treatment panel.
- **i18n** — new `soil` namespace in `en.json` and `hi.json` (all UI chrome
  localized; content remains English from the seed catalog).

## 3. Test Results

### 3.1 Backend (`tests/test_soil_recommendations.py` — 18 new tests)
Seeding: active catalog built (26 plans), idempotency, distinct tomato vs.
potato soil notes for the same disease name, version-bump deactivation.
Endpoints: auth required, unseeded-catalog 503, catalog metadata, full disease
plan shape (nine areas + health profile), 404 for unknown disease, 422 for an
invalid severity. Scoring: baseline good (4.0) for tomato, severe→3.0 (good→fair),
low-confidence note + penalty, low-confidence scan isolation. Scan lookup: happy
path (scan severity/confidence echoed), by-name fallback, no-plan 404, unknown
scan 404.

**Full backend suite: `250 passed, 1 skipped` · coverage `85%`** (was 232/84%).
Ruff: **All checks passed**. MyPy: **Success (61 files)**.

### 3.2 Frontend
**`soil-recommendations.test.tsx` — 9 new tests** covering panel loading / 404
empty / error-with-retry / success states and the view's health header, notes,
expand/collapse behaviour and micronutrient chips.

**Full frontend suite: `72 passed` (14 files)** (was 63/13).
TypeScript `tsc -b --noEmit`: **clean**. ESLint `--max-warnings=0`: **clean**.
Production `vite build`: **OK** (pre-existing chunk-size warning only).

## 4. Files Changed / Added

- **Backend (new):** `app/models/soil.py`, `app/schemas/soil.py`,
  `app/services/soil.py`, `app/db/soil_seed_data.py`,
  `app/api/v1/endpoints/soil.py`, `alembic/versions/c5e1f3a7b9d2_*.py`,
  `tests/test_soil_recommendations.py`
- **Backend (modified):** `app/db/seed.py`, `app/models/__init__.py`,
  `app/api/v1/router.py`, `app/api/v1/endpoints/scans.py`, `app/main.py`
- **Frontend (new):** `src/types/soil.ts`,
  `src/components/treatment/soil-recommendations.tsx`,
  `src/components/__tests__/soil-recommendations.test.tsx`
- **Frontend (modified):** `src/lib/api.ts`, `src/locales/en.json`,
  `src/locales/hi.json`, `src/pages/scan-crop.tsx`, `src/pages/scan-detail.tsx`

## 5. Future-Ready Notes

- **Weather / location / soil-test data** plug into `SoilContext` as new
  optional fields and feed the existing `health()` scoring pipeline — the
  schema, service signature and endpoints do not need to change.
- **Catalog versioning** means soil content can be corrected or extended with a
  single version bump + reseed (no code changes).
- **Restart the dev backend** to pick up the new `/soil` routes (it was started
  without `--reload`).

**Next:** M3 Task 4 — awaiting user approval; do not begin unprompted.
