# M3 Task 1 Completion Report — Smart Treatment Recommendation Engine

**Milestone:** M3 · **Task:** 1 · **Status:** Implemented — awaiting approval
**Branch:** `main` · **Date:** 2026-08-05

---

## 1. Overview

Task 1 adds a **versioned, data-driven treatment recommendation engine** for
every disease in the knowledge catalog. Each disease now maps to a complete,
beginner-friendly care plan covering **disease-level facts** (overview, cause,
symptoms, severity, spread mechanism) and **all twelve treatment categories**:

1. Homemade remedies — kitchen ingredients / homemade sprays / traditional
2. Organic remedies — neem oil / bio-fungicides / organic pesticides / nutrients
3. Chemical recommendations — fungicides / insecticides / bactericides with
   dosage, application interval and safety precautions
4. Fertilizer · 5. Watering · 6. Sunlight · 7. Temperature · 8. Humidity
9. Prevention tips · 10. Recovery timeline · 11. Isolation · 12. Monitoring advice

The content is **not hardcoded anywhere in controllers** — it lives entirely in
the seeded database. The API is a thin read-only layer over the active catalog.
The catalog is **versioned**: exactly one version is active at a time, and
bumping the version atomically swaps the active plan set.

**Scale:** 12 crops · 26 diseases · 26 curated plans (one per disease), each
self-contained across all twelve categories.

## 2. Features Implemented

### 2.1 ORM models (`app/models/recommendation.py`)
- **`RecommendationCatalog`** — one row per catalog version (`version` unique,
  `is_active` boolean). The seeder keeps exactly one active; activating a new
  version deactivates the previous one atomically.
- **`DiseaseRecommendation`** — one complete plan per `(catalog_id, disease_id)`
  (unique constraint `uq_recommendation_catalog_disease`). Repeatable content
  (symptoms, remedies, chemicals, prevention tips, monitoring advice) is stored
  as JSON; the environment + care guidance (watering, sunlight, temperature,
  humidity, fertilizer, isolation, recovery timeline) as text.
- Both registered in `app/models/__init__.py` so Alembic autogenerate and test
  `create_all` see them.

### 2.2 API schemas (`app/schemas/recommendation.py`)
- Nested item DTOs give each category a **stable, structured shape** (no prose
  parsing on the client): `HomemadeRemedyOut` (title/category/ingredients/
  instructions/frequency), `OrganicRemedyOut` (title/category/application/
  frequency), `ChemicalRecommendationOut` (category/product/dosage/application
  interval/safety precautions).
- `DiseaseRecommendationOut` — the self-contained plan payload (with a worked
  Late-Blight example in the OpenAPI schema).
- `RecommendationCatalogOut` — active-catalog metadata (version, plan count).
- Category vocabularies exposed as module constants so seeds and docs agree.

### 2.3 Curated catalog + seeder (`app/db/recommendation_seed_data.py`, `app/db/seed.py`)
- **26 curated plans** keyed by `(crop common_name, disease name)` — crops are
  disambiguated because the catalog reuses names across crops (both tomato and
  potato have `Late Blight`).
- Written for Indian field conditions: affordable kitchen ingredients, doses in
  grams/litres from extension literature, plain-language safety steps.
- The seeder **merges** curated content with the existing `Disease` row fields
  (symptoms, cause, prevention tips, recovery time, M1 remedy lists) so every
  plan is complete even before it is curated — curated fields win, catalog
  fields fill the gaps.
- **Idempotent** by catalog version + disease; re-running `python -m app.db.seed`
  creates zero duplicates. `_fallback_plan` wraps un-curated diseases' flat M1
  lists into the same structured shapes, so adding a new disease to the catalog
  automatically gets a valid (if generic) plan.

### 2.4 Service (`app/services/recommendations.py`)
- `RecommendationService` — read-only resolver against the active catalog:
  - `catalog()` → metadata + plan count,
  - `for_disease(disease_id)` → full plan,
  - `for_scan(scan)` → plan for a scan's prediction (by `disease_id`, then
    falling back to a disease-name match so unmapped predictions still resolve).
- Domain exceptions `RecommendationNotFoundError` (404) and
  `CatalogUnavailableError` (503 when the seeder never ran) mapped in `main.py`.

### 2.5 API endpoints
- `GET /recommendations/catalog` — active catalog metadata (auth-gated, like the
  M2 catalog endpoint).
- `GET /recommendations/diseases/{disease_id}` — full plan for one disease.
- `GET /scans/{scan_id}/recommendations` — plan for the disease a scan predicted
  (reuses the scan ownership guard; `404` for missing/other-user's scans).

### 2.6 Migration
- `alembic/versions/b4d2e6f8a1c3_add_recommendation_catalog.py` (head) creates
  `recommendation_catalogs` + `disease_recommendations`; dev DB migrated and
  seeded (`26 plans`).

## 3. Adding a new disease

1. Add the disease to `app/db/seed_data.py` (catalog) — the seeder auto-creates
   a structured plan from the M1 fields.
2. Optionally add a curated entry to `RECOMMENDATIONS` in
   `app/db/recommendation_seed_data.py` (keyed by `(crop common_name, disease
   name)`) for a full bespoke plan.
3. Bump `RECOMMENDATION_VERSION` to activate a new catalog version (old versions
   stay queryable by metadata, the active one swaps atomically).
4. Run `python -m app.db.seed`.

## 4. Testing & gates

**Backend tests** — new `tests/test_recommendations.py` (13 tests): seeder build
+ idempotency, crop-disambiguation (tomato vs potato `Late Blight`), version-bump
deactivation, catalog-unavailable 503, auth 401, catalog metadata, per-disease
plan structure (all twelve categories + chemical dict shape), unknown-disease
404, and the `/scans/{id}/recommendations` path (happy path, by-name fallback,
no-plan 404, ownership/unknown 404).

**Gates (all clean):** `pytest` — **232 passed, 1 skipped** (M2.1 baseline 219 + 13),
**85% coverage** (M2.1 was 84%); `ruff check .`; `ruff format --check .`;
`mypy app` (56 files, no issues). Frontend untouched (no UI changes in Task 1) —
the app consumes these endpoints in Task 2.
