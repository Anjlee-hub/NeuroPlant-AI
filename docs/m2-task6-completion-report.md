# M2 Task 6 Completion Report — Offline Queue / Sync

**Milestone:** M2 · **Task:** 6 (6.1–6.4) · **Status:** Implemented — awaiting approval
**Branch:** `main` · **Date:** 2026-08-05

---

## 1. Overview

Task 6 lets the offline PWA queue drain to the server. Live uploads
(`POST /scans` multipart) and queued offline scans (`POST /scans/sync` JSON
batch) now run through the **exact same** detection pipeline — validation,
preprocessing, inference, Grad-CAM explainability, persistence, and error
handling are one shared implementation with zero online/offline drift. The
sync endpoint reconciles a whole queue in a single request, is idempotent per
`client_scan_id`, isolates each item in its own transaction, and reports
per-item `created | replayed | failed` outcomes so a partial failure is
repairable and replayable. All work is committed on `main`; the working tree
is clean.

Sub-tasks: **6.1** sync schemas → **6.2** pipeline bytes-input unification →
**6.3** `POST /scans/sync` endpoint + guards + API tests → **6.4** OpenAPI
contract + full-workflow verification (this report).

## 2. Features Implemented

### 6.1 — Sync request/response schemas (`app/schemas/scan.py`)
- **`SyncImageIn`** — one base64-encoded image (`data`, `content_type`,
  optional `filename`).
- **`ScanSyncItemIn`** — one queued scan, mirroring the multipart upload fields
  (`client_scan_id` UUID pattern, `images` min1, `crop_id`, `part_type`,
  `device_id`) with a worked request example.
- **`SyncErrorOut`** — machine-readable per-item failure (`code` + `message`).
- **`ScanSyncResultOut`** — per-item outcome (`created | replayed | failed`,
  authoritative `ScanOut` on success, `error` on failure).
- **`ScanSyncOut`** — batch envelope (`total / created / replayed / failed`)
  with a worked response example.
- **`ScanCreate.synced_at`** — optional timestamp the sync path stamps.

### 6.2 — Pipeline unification (`app/services/scan_pipeline.py`)
- **Common internal representation** — both multipart `UploadFile`s and
  base64 `SyncImageIn`s are adapted into `app.ai.types.ImageData` before any
  processing (`_image_from_upload` / `_image_from_sync`; the sync adapter
  raises `ImageRejectedError` for invalid base64).
- **`_process_images` shared run core** — count/idempotency checks, validate →
  sanitize → store, preprocessing, inference, Grad-CAM, and persistence are
  one implementation used by both `process_upload` and the new
  `process_sync_item`. Only the raw-input adapters differ.
- **`ScanService.create`** now persists `synced_at`; sync rows carry
  `source_type="sync"` media items and a `synced_at` stamp.

### 6.3 — `POST /scans/sync` endpoint (`app/api/v1/endpoints/scans.py`)
- **JSON batch** of `ScanSyncItemIn`; each item processed independently —
  one failure never blocks the rest, and each item commits in its own
  transaction (a batch is never half-applied).
- **Idempotency** — a single batch-wide `ScanService.find_by_client_ids`
  query short-circuits replays; already-persisted ids return their existing
  authoritative row as `replayed` without re-entering the pipeline. Works for
  duplicates within a batch too (first `created`, second `replayed`).
- **Auth & security** — bearer required; replays are owner-scoped and a
  cross-user `client_scan_id` (globally unique) fails per-item with
  `duplicate_client_scan_id` rather than leaking another user's scan. A
  dedicated `scan_sync_rate_limit` (separate budget from live uploads, keyed
  user+IP) returns 429 when exhausted.
- **Payload guards** — empty batch → 422 `empty_batch`; `>
  scan_sync_max_items` (default 50) → 413 `batch_too_large`; malformed items
  (bad UUID, empty `images`, missing `content_type`, bad `part_type`) → 422
  via schema validation.
- **`ScanOut.synced_at`** — exposed so sync responses confirm the server
  stamp; `sync_status` stays `synced` because the server row is authoritative.

### 6.4 — Verification (this report)
- **OpenAPI** — worked examples on `ScanSyncItemIn` (request) and
  `ScanSyncOut` (response); `tests/test_openapi_sync.py` (4 tests) pins the
  operation (bearer security, array-of-`ScanSyncItemIn` request body,
  `ScanSyncOut` 200, full per-item contract).
- **Full offline workflow** — `test_sync_offline_queue_drain_and_retry`
  exercises queue → batch sync → partial failure → repair & retry (same id) →
  full re-sync replaying every row.
- **Flake/warning hygiene** — replaced deprecated
  `HTTP_413_REQUEST_ENTITY_TOO_LARGE` with `HTTP_413_CONTENT_TOO_LARGE`; the
  suite runs warning-clean.

## 3. API Endpoints (`/api/v1`)

| Method | Path | Auth | Purpose |
|---|---|---|---|
| POST | `/scans/sync` | bearer | Batch reconciliation of the offline queue (idempotent, per-item `created \| replayed \| failed`) |

`POST /scans` is unchanged (201 created / 200 idempotent replay) and shares
the same pipeline service.

## 4. Architecture Changes

```
multipart UploadFile ──┐
                       ├─> ImageData ──> _process_images (single run core)
base64 SyncImageIn ────┘     │            validate → sanitize → store
                             │            → preprocess → infer → Grad-CAM
                             │            → persist (own transaction)
        POST /scans    ──────┘            process_upload
        POST /scans/sync ──────────────── process_sync_item  (+ synced_at)
```

- `ScanPipelineService` gains `process_sync_item` and the shared
  `_process_images`; `_validate_and_store` now consumes `ImageData`.
- `ScanService.find_by_client_ids` — one batch idempotency query.
- `RateLimiter` gains a second budget: `get_scan_sync_limiter` +
  `scan_sync_rate_limit` dependency; settings `rate_limit_scan_sync_per_minute`
  and `scan_sync_max_items`.

## 5. Database Changes

**No schema migration.** `scans.synced_at`, `sync_status`, `sync_error`, and
`device_id` were prepared in Task 4.1; Task 6 now uses `synced_at` (stamped by
the sync path) and leaves `sync_status` at its `synced` default (server rows
are authoritative). Heatmap PNGs remain storage artifacts, not rows.

## 6. Test Results

| Suite | Result |
|---|---|
| Backend `pytest` (full) | **214 passed, 1 skipped**, **92% coverage** |
| — Sync run (pipeline, sync API, OpenAPI sync) | **29 passed** |
| `ruff check .` | clean |
| `ruff format --check .` | 69 files formatted |
| `mypy app` | clean (49 source files) |
| `pip check` | no broken requirements |

Coverage highlights: `app/services/scan_pipeline.py` **94%**,
`app/services/scans.py` **96%**, `app/core/rate_limit.py` **91%**,
`app/api/v1/deps.py` **80%**, `app/api/v1/endpoints/scans.py` **70%**
(explain/soft-delete branches), `app/schemas/scan.py` fully covered.

## 7. Verification Performed (Task 6.4)

| # | Acceptance item | Evidence (tests) |
|---|---|---|
| 1 | **Offline queue → batch sync** | `test_sync_success_batch`, `test_sync_offline_queue_drain_and_retry` |
| 2 | **Idempotent replay** | `test_sync_duplicate_client_scan_id_replays`, `test_sync_duplicate_within_batch`, `test_sync_offline_queue_drain_and_retry` (full re-sync replays) |
| 3 | **Partial failure handling** | `test_sync_partial_failure_continues`, `test_sync_mixed_batch_statuses` |
| 4 | **Conflict resolution** | `test_sync_cross_user_duplicate_rejected` (owner-scoped replay, per-item `duplicate_client_scan_id`) |
| 5 | **Retry behavior** | `test_sync_offline_queue_drain_and_retry` (repair + retry same id → created) |
| 6 | **OpenAPI docs** | `test_openapi_declares_sync_operation`, `test_openapi_sync_request_is_item_array`, `test_openapi_sync_schemas_carry_full_contract`, `test_openapi_sync_explains_with_examples` |
| 7 | **Authentication** | `test_sync_requires_auth` (401) |
| 8 | **Rate limiting** | `test_sync_rate_limited` (429 after budget exhausted) |
| 9 | **Payload validation** | `test_sync_empty_batch_rejected` (422), `test_sync_batch_too_large_rejected` (413), `test_sync_malformed_item_rejected` (422) |
| 10 | **Error responses** | `test_sync_inference_failure_reports_failed` (`inference_failed`), per-item `error.code` in partial-failure tests |
| 11 | **Pipeline parity (online = offline)** | `test_sync_item_matches_upload_pipeline`, `test_sync_item_persists_scan_and_images`, `test_sync_item_multiple_images_all_stored`, `test_sync_item_replay_returns_existing_row`, `test_sync_item_*_rejected/maps_to_*` (12 pipeline tests) |

## 8. Known Limitations

1. **Rate limiter is in-process** (single instance). Distributed enforcement
   via Redis is deferred to M11 hardening; on a multi-replica deploy the budget
   is per-instance until then.
2. **`client_scan_id` is globally unique.** A second user syncing an id another
   user already used gets a per-item `duplicate_client_scan_id` failure (never
   a silent replay of someone else's scan) — secure by design, but the id is
   single-owner.
3. **Client queue is frontend.** The PWA IndexedDB drain itself is out of
   backend scope; the backend contract is verified end-to-end over HTTP.
4. **Sync requires a live bearer token.** Expired tokens fail the whole
   request (401) rather than per item; offline re-auth is outside M2.
5. **Sequential per-item inference.** A batch runs items one-by-one to bound
   CPU/DB contention on the SQLite dev fallback; parallel per-item inference
   is a production tuning option (needs pooled connections).

## 9. Performance Notes

- **One idempotency query per batch.** `find_by_client_ids` resolves every
  replay in a single `WHERE client_scan_id IN (...)`; replayed items never
  re-enter the detection pipeline (no re-inference, no image decode).
- **Per-item transactions.** Each scan commits independently, so a batch is
  never half-applied and one item's failure rolls back only itself — failures
  leave no partial rows (the pipeline is also clean about storage orphans: a
  failed inference simply never persisted a row).
- **Replay is O(1) DB work** — batched lookup + serialization of the existing
  row.
- **Detection cost is paid once per unique item**; the drain-and-retry test
  confirms a full re-sync of already-landed items is purely `replayed`.

## 10. Commit History (Task 6)

```
<this commit>        test+docs: M2 Task6.4 — OpenAPI sync contract, workflow test, report
57f7116 feat(scans): add POST /scans/sync offline batch endpoint (M2, Task 6.3)
103b732 refactor(scans): unify online/offline scan pipeline (M2, Task 6.2)
9c27d74 feat(scans): add offline sync schemas (M2, Task 6.1)
```

## 11. Files (Task 6)

```
backend/app/schemas/scan.py               backend/app/services/scan_pipeline.py
backend/app/services/scans.py             backend/app/api/v1/endpoints/scans.py
backend/app/api/v1/deps.py                backend/app/core/config.py
backend/app/core/rate_limit.py
backend/tests/test_scan_pipeline.py       (sync-path section)
backend/tests/test_scan_sync_api.py       (new)
backend/tests/test_openapi_sync.py        (new)
docs/m2-task6-completion-report.md        (new)
```

---

**Next:** M2 Task 7 (offline queue persistence / PWA offline UX, or as defined
in the milestone plan) — awaiting approval.
