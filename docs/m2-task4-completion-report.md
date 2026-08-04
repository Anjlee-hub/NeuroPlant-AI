# M2 Task 4 Completion Report — AI Disease Detection Scan API

**Milestone:** M2 · **Task:** 4 (4.1–4.4) · **Status:** Implemented — awaiting approval
**Tag:** `v0.2.0-task4` · **Branch:** `main`
**Date:** 2026-08-04

---

## 1. Overview

Task 4 delivers the disease-detection scan API: image upload with AI prediction,
persistent scan records, and a full history surface (list/detail/delete). The
pipeline is storage- and classifier-agnostic behind interfaces; scans are
soft-deleted with an audit trail; the API is documented, rate-limited, and
covered by unit, service, and HTTP integration tests. All work is committed on
`main` and the working tree is clean.

Sub-tasks: **4.1** scan persistence + storage abstraction → **4.2** `POST /scans`
upload + prediction pipeline → **4.3** scan history API (list/detail/delete) →
**4.4** final verification + quality gates (this report).

## 2. Features Implemented

### 4.1 — Persistence & storage abstraction
- **`Scan` model** (`app/models/scan.py`) — `client_scan_id` (idempotency key,
  unique), `media_items`/`ai_metadata` JSON columns, prediction fields
  (disease, confidence, severity, stage), model/dataset versions, AI provider,
  per-stage processing times, sync state (`sync_status`/`sync_error`/`synced_at`),
  `device_id`, `image_path`/`processed_image_path`/`heatmap_path`.
- **`StorageService` protocol** (`app/services/storage.py`) — `save`/`delete`/`url`.
  `LocalStorageService` is the dev/default; an S3/R2-backed service slots in
  behind the same interface for production (M11). The pipeline only talks to
  the protocol.

### 4.2 — Upload + detection pipeline
- **`POST /scans`** (multipart) — one or more images + form fields
  (`client_scan_id`, `crop_id`, `part_type`, `device_id`). Validates image
  type/size, enforces `client_scan_id` UUID format, rejects unknown `part_type`,
  applies an upload rate limit.
- **`ScanPipelineService`** (`app/services/scan_pipeline.py`) — orchestrates
  storage → preprocessing → inference → persistence, bounded by
  `max_images` and an inference timeout; maps failures to typed errors with
  machine codes.
- **Idempotent replay** — re-posting a known `client_scan_id` returns `200`
  with the previously stored scan instead of re-running inference (`201` on
  first creation).

### 4.3 — Scan history API
- **`GET /scans`** — pagination (`page`/`page_size`, max 100, `has_next`),
  sorting (`created_at`|`confidence`|`disease_name`, asc/desc), free-text
  search (disease or provider), filters: `date_from`/`date_to`, `crop_id`,
  `disease`, `part_type`, `confidence_min`/`max`, `severity`, `sync_status`,
  and admin-only `owner_id` narrowing. Invalid combinations (inverted
  confidence range, out-of-range pagination) return `422`.
- **`GET /scans/{id}`** — complete detail record.
- **`DELETE /scans/{id}`** — soft delete (`deleted_at`) + append-only
  `audit_logs` row in one transaction; `204` on success.
- **Security** — users only see their own scans; admins see all; the **same
  `404`** is returned for missing, soft-deleted, or other-owned scans
  (enumeration guard). Deleted scans never resurface via history, detail, or
  the offline idempotency lookup.

## 3. API Endpoints (`/api/v1`)

| Method | Path | Auth | Purpose |
|---|---|---|---|
| POST | `/scans` | bearer | Upload + detect (201; 200 idempotent replay) |
| GET | `/scans` | bearer | Paginated/filterable history |
| GET | `/scans/{scan_id}` | bearer | Full scan detail |
| DELETE | `/scans/{scan_id}` | bearer | Soft delete (204) |

Rate limit on `POST /scans` (`scan_upload_rate_limit`). OpenAPI documents all
four paths, the 15 query parameters on `GET /scans`, and `ScanOut`/`ScanListOut`
response schemas with request/response examples.

## 4. Database Changes

New Alembic migrations (applied on top of M1's `e7a4341cf99e`):

| Revision | Change |
|---|---|
| `5c9a2e7f41b0` | Add `scans` table (M2 disease detection) |
| `a3f9c8b2d1e4` | Add `scans.deleted_at`, composite index `ix_scans_user_deleted_created`, new `audit_logs` table + indexes |

**New tables:** `scans` (Task 4.1), `audit_logs` (Task 4.3).
**New columns:** `scans.deleted_at` (nullable, soft delete).
**New indexes:** `ix_scans_user_deleted_created` (history query),
`ix_scans_client_scan_id` (unique idempotency key), plus existing scan FK/column
indexes. **Verified:** clean `upgrade head` → `downgrade base` → `upgrade head`
on a fresh SQLite database (13 tables after upgrade).

## 5. Test Results

| Suite | Result |
|---|---|
| Backend `pytest` (full) | **142 passed**, 85% coverage |
| — API integration (`test_auth`, `test_health`, `test_scan_api`, `test_scan_history_api`) | **64 passed** |
| — Scan services (`test_scans`) | all passed |
| `ruff check .` | clean |
| `ruff format --check .` | 61 files formatted |
| `mypy app` | clean (47 source files) |
| `pip check` | no broken requirements |

Coverage highlights: `app/services/scans.py` **99%**, `app/services/scan_pipeline.py`
**93%**, `app/api/v1/endpoints/scans.py` **91%**, `app/ai/opencv_preprocess.py`
**97%**. The API tests exercise upload, prediction + idempotent replay, history,
pagination, search, sorting, every filter, detail, delete (204/404), ownership
isolation, admin access, soft-delete hiding, and audit-log writes.

## 6. Verification Performed (Task 4.4)

- **Full test suite + coverage** — 142 passed / 85%.
- **API integration suite** — 64 passed across auth, health, scan upload, and
  scan-history HTTP tests.
- **Quality gates** — ruff check, ruff format check, mypy, `pip check` all clean.
- **Fresh-DB migrations** — `alembic upgrade head` on a new SQLite DB created
  all 13 tables with correct columns/indexes; downgrade to base and re-upgrade
  both clean.
- **OpenAPI** — `/api/v1/openapi.json` lists all four scan paths; `GET /scans`
  declares all 15 query params; `ScanOut`/`ScanListOut` carry examples;
  `POST /scans` documents multipart form + file fields.

## 7. Known Limitations

1. **Storage is local filesystem in dev.** `StorageService` abstracts S3/R2,
   but the S3 implementation is not wired until M11 deployment. Local paths are
   used in dev/tests (`STORAGE_LOCAL_DIR`).
2. **SQLite dev fallback vs Postgres prod.** History queries are tested on
   SQLite (`sqlite+aiosqlite`); timestamps are stored naive-UTC to match
   SQLite's round-trip. The Postgres/asyncpg path is exercised at deploy time.
3. **Offset pagination.** `page`/`page_size` with `OFFSET` is fine at current
   scale; keyset/cursor pagination would be preferable for very deep history
   (future optimization).
4. **Soft-deleted scan files are not removed from storage.** Deleting keeps the
   row for audit; object cleanup is intentionally out of scope (a purge worker
   is a possible later task).
5. **Rule-baseline classifier is the serving model.** Real trained artifacts
   replace the baseline behind the same `DiseaseClassifier` interface when the
   training pipeline ships (later M2 tasks / M4).
6. **Rate limiting disabled by default** (`rate_limit_enabled=False`); the
   upload limiter is registered but must be enabled in production.
7. **OpenAPI examples are component-level.** They render in the schema and
   Swagger UI; per-operation response examples could be added for extra
   discoverability.

## 8. Performance Notes

- **No N+1** — scan media/rankings are JSON columns, not relationships, so
  list/detail are single SELECT (+ COUNT) queries.
- **Composite index** `ix_scans_user_deleted_created` serves the default
  history query (user + non-deleted + created_at order).
- **Sort columns are whitelisted** (`_SORT_COLUMNS`); client input never maps
  directly into `ORDER BY`.
- **Idempotency key** `client_scan_id` (unique) prevents duplicate inference on
  retries — an offline-sync safety property (Task 6 reuses it).
- **Rate limit on upload** protects the inference path.

## 9. Commit History (Task 4)

```
b1564c3 M2 Task4.3: scan history API - list/detail/delete with soft delete, audit, filters, admin access
dfd5eb1 M2 Task 4.2: POST /scans upload endpoint + scan pipeline
bfc1556 feat(ai): M2 Task4.1 — scan persistence + storage abstraction
```

## 10. Files (Task 4)

```
backend/app/models/scan.py        backend/app/models/audit.py          (new)
backend/app/models/__init__.py    backend/app/schemas/scan.py
backend/app/services/scans.py     backend/app/services/storage.py
backend/app/services/scan_pipeline.py   backend/app/services/detection.py
backend/app/ai/opencv_preprocess.py     backend/app/ai/preprocess.py
backend/app/ai/classifiers.py           backend/app/api/v1/endpoints/scans.py
backend/app/main.py
backend/alembic/versions/5c9a2e7f41b0_add_scans_table.py
backend/alembic/versions/a3f9c8b2d1e4_add_scan_soft_delete_and_audit.py
backend/tests/test_scans.py             backend/tests/test_scan_api.py
backend/tests/test_scan_history_api.py  backend/tests/test_scan_pipeline.py
backend/tests/test_storage.py           backend/tests/test_detection.py
backend/tests/test_preprocess.py        backend/tests/test_ai.py
```

---

**Next:** M2 Task 5 (Grad-CAM explainability) — awaiting approval.
