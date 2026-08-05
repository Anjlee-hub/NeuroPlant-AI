# M2 Task 5 Completion Report — Grad-CAM Explainability

**Milestone:** M2 · **Task:** 5 (5.1–5.5) · **Status:** Implemented — awaiting approval
**Branch:** `main` · **Date:** 2026-08-05

---

## 1. Overview

Task 5 delivers Grad-CAM explainability for the disease-detection scan API: the
prediction pipeline generates and persists per-scan heatmaps, and a dedicated
explain endpoint (`GET /scans/{id}/explain`) returns the heatmap + overlay, a
plain-language explanation, ranked top-5 candidates, confidence band with expert
advice, model/dataset provenance, and pipeline timing — all read from facts
captured at prediction time, **without re-running inference**. Explainability is
best-effort (a heatmap failure never fails the diagnosis) and authorization is
strict (the endpoint reveals nothing about other users' or soft-deleted scans).
All work is committed on `main`; the working tree is clean.

Sub-tasks: **5.1** Grad-CAM core module + storage read → **5.2** explainability
wired into detection + scan pipeline → **5.3** `GET /scans/{id}/explain`
endpoint + schemas + API tests → **5.4** timing fields, OpenAPI docs, unit tests
→ **5.5** final verification + quality gates (this report).

## 2. Features Implemented

### 5.1 — Grad-CAM core (`app/ai/gradcam.py`)
- **`ExplainabilityProvider`** structural protocol (`app/ai/types.py`) —
  `provider_name` + `heatmap(image, class_name) -> HeatmapResult`; declared as a
  `@property` on the `DiseaseClassifier` protocol (read-only, covariant for mypy).
- **`TensorFlowGradCAM`** — lazy (imports TF on first use, fails to
  `ModelUnavailableError` when TensorFlow is absent or the artifact is missing),
  picks the last conv layer, produces a normalized heatmap.
- **`RuleBaselineSaliency`** — deterministic, artifact-free saliency fallback so
  explainability works offline/untrained; used by the rule-baseline classifier.
- **`HeatmapResult`** + PNG encoding helpers — raw grayscale PNG
  (`encode_heatmap_png`), Jet overlay blending (`apply_heatmap_overlay`,
  clamped opacity), `encode_rgb_png`; a **lossless round-trip test**.
- **`StorageService.read()`** added so heatmaps are retrievable by key.

### 5.2 — Explainability wired into detection + pipeline
- **`DetectionService`** exposes the classifier's `explainer`, a
  `generate_heatmap()` / `generate_heatmap_async()` seam (thread-offloaded), and
  `confidence_level()` (high ≥ 0.85, medium ≥ 0.60, low).
- **`ScanPipelineService`** generates the heatmap best-effort after prediction,
  stores **raw grayscale + Jet overlay** PNGs under `{user}/heatmaps/`, sets
  `scan.heatmap_path` (→ overlay) and records `grad_cam` provenance
  (provider, class, `time_ms`, raw key) plus `top5`, `confidence.level`, and
  `model` metadata inside the `ai_metadata` JSON column.
- **Classifiers** — `RuleBaselineClassifier` exposes `RuleBaselineSaliency`;
  `LocalTensorFlowClassifier` exposes a lazy `TensorFlowGradCAM` bound to the
  loaded model. TOP_K raised 3 → 5.

### 5.3 — Explain endpoint (`GET /scans/{id}/explain`)
- **`ExplainService`** (`app/services/explain.py`) composes the payload from
  stored scan state — storage URLs for raw + overlay, plain-language
  explanation, ranked top-5, confidence band + **expert advice** (low-confidence
  scans get a "verify before treating" nudge), Grad-CAM provenance, model
  metadata, and catalog symptoms (one lookup). No re-inference.
- **`ScanExplainOut`** schema with nested disease / confidence / heatmap / model
  DTOs. **Graceful degradation**: a scan without a heatmap still explains the
  diagnosis, with heatmap fields `None`.
- **Ownership guard** — same `404` for missing, soft-deleted, or other-user's
  scans (enumeration-safe).

### 5.4 — Timing + OpenAPI + unit tests
- **`ExplainTimingOut`** block on the payload: `preprocessing_time_ms`,
  `inference_time_ms`, `processing_time_ms` (from the scan row) and
  `heatmap_time_ms` (Grad-CAM generation; `None` when absent).
- **OpenAPI** — per-field descriptions across all explain DTOs and a worked
  example payload on `ScanExplainOut`.
- **`tests/test_explain_service.py`** — 12 unit tests driving the service
  directly (no HTTP): payload composition, URL resolution, confidence bands +
  advice, explanation text, no-heatmap degradation, timing edges, symptom lookup.

### 5.5 — Final verification (this report)
Full suite + explainability integration run, acceptance-item verification,
lint/type/OpenAPI gates, and a **flaky-test fix**: `test_predict_async_matches_sync`
compared full `ScanResult` equality including the measured latency, which rounds
to `0.0` vs `0.1` between two sub-millisecond runs of the fake classifier; the
comparison now normalizes `inference_time_ms` out of it.

## 3. API Endpoints (`/api/v1`)

| Method | Path | Auth | Purpose |
|---|---|---|---|
| GET | `/scans/{scan_id}/explain` | bearer | Explainability payload: heatmap + overlay, explanation, top-5, confidence + advice, timing, model metadata |

Bearer security is declared in the OpenAPI operation. Response `200` → `ScanExplainOut`;
`404` for missing / soft-deleted / other-owned scans; `401` unauthenticated.

## 4. Database Changes

**None.** Task 5 stores explainability through existing columns added in Task
4.1: `scans.heatmap_path` (overlay key) and the `scans.ai_metadata` JSON column
(now holding `top5`, `confidence`, `model`, `grad_cam`). Heatmap PNGs are
storage artifacts under `{user}/heatmaps/`, not database rows.

## 5. Test Results

| Suite | Result |
|---|---|
| Backend `pytest` (full) | **185 passed, 1 skipped**, 84% coverage |
| — Explainability run (gradcam, detection, scan pipeline, scan API, explain API/service, OpenAPI) | **77 passed, 1 skipped** |
| `ruff check .` | clean |
| `ruff format --check .` | 67 files formatted |
| `mypy app` | clean (49 source files) |
| `pip check` | no broken requirements |

Coverage highlights (explainability run): `app/services/explain.py` **97%**,
`app/services/detection.py` **93%**, `app/services/scan_pipeline.py` **93%**,
`app/ai/gradcam.py` **68%** (the TensorFlow branch lines are unexercised — TF is
not installed; that path is covered by its failure-mode tests).

## 6. Verification Performed (Task 5.5)

| # | Acceptance item | Evidence (tests) |
|---|---|---|
| 1 | **Grad-CAM generation** | `test_generate_heatmap_returns_heatmap_result`, `test_generate_heatmap_async_matches_sync`, `test_saliency_heatmap_shape_and_range`, `test_saliency_is_deterministic`, `test_rule_baseline_exposes_saliency_explainer`, `test_tf_gradcam_missing_tensorflow_raises_inference_error` |
| 2 | **Heatmap storage** | `test_heatmap_png_roundtrip_is_lossless`, `test_rgb_png_encodes`, `test_overlay_*` (opacity/clamp/resize/color), `test_scan_stores_top5_confidence_and_model_metadata`, `test_heatmap_failure_degrades_gracefully`, `test_upload_persists_scan_and_images` |
| 3 | **Explain API** | `test_explain_returns_full_payload`, `test_explain_degrades_without_heatmap`, `test_explain_low_confidence_carries_advice` |
| 4 | **Confidence levels** | `test_confidence_level_bands`, `test_confidence_level_and_advice[high/medium/low]`, `test_explain_low_confidence_carries_advice` |
| 5 | **Top-5 predictions** | `test_scan_stores_top5_confidence_and_model_metadata`, `test_predict_preserves_rankings`, `test_top5_empty_without_metadata`, `test_build_composes_full_payload` |
| 6 | **Plain-language explanations** | `test_explanation_includes_facts`, `test_explanation_omits_heatmap_and_stage_when_absent`, `test_explain_returns_full_payload` |
| 7 | **Model metadata** | `test_predict_builds_enriched_scan_result`, `test_predict_falls_back_to_classifier_model_info`, `test_local_tf_provider_metadata`, `test_build_composes_full_payload`, `test_explain_returns_full_payload` (version round-trip) |
| 8 | **Authorization** | `test_explain_404_for_other_users_scan`, `test_explain_404_for_missing_scan`, `test_openapi_declares_explain_operation` (bearer documented); Task 4 ownership/soft-delete suite still green |

Additional gates: full suite (185 passed), explainability integration run
(77 passed), ruff/format/mypy/pip-check clean, and OpenAPI verification
(`tests/test_openapi_explain.py`) asserting the explain operation exists under
bearer auth, its `200` response resolves to `ScanExplainOut`, and that component
lists the full contract (disease, confidence+advice, top5, heatmap/overlay,
explanation, timing, model) with a worked example.

## 7. Known Limitations

1. **TensorFlow path unexercised locally.** No TF install in the dev env; the
   `TensorFlowGradCAM` path is lazy and guarded by failure-mode tests. The
   deterministic rule-baseline explainer serves in dev/tests.
2. **Heatmaps are not served over HTTP yet.** `StorageService.url()` returns
   `/media/{key}` (a valid storage key) but no static media mount exists until
   deployment (M11); the explain payload's URLs are storage-resolvable, not yet
   publicly fetchable.
3. **Sub-millisecond baseline timing.** The rule-baseline classifier is so fast
   that `inference_time_ms` can round to `0.0`; API tests assert shape and
   internal consistency rather than positive latency (exact values are pinned by
   the `ExplainService` unit tests).
4. **Explain reads stored facts only.** A scan whose heatmap was never produced
   (e.g. heatmap failure at upload) still explains the diagnosis with heatmap
   fields `None` — intentional, not an error path.

## 8. Performance Notes

- **No re-inference on explain** — the payload is assembled from stored scan
  state (heatmap keys, top-5, timings, provenance) plus a single catalog symptom
  lookup; the endpoint is O(1) DB work.
- **Heatmap generation is best-effort and offloaded** — runs in a worker thread
  (`run_in_threadpool`) under the scan inference timeout; a failure is logged and
  swallowed so the diagnosis stands.
- **Two PNGs per heatmap** — raw grayscale map kept alongside the Jet overlay so
  it can be re-blended at any opacity without re-running Grad-CAM.
- **Content-addressed storage keys** — never client-supplied; no path traversal
  or name-collision risk.

## 9. Commit History (Task 5)

```
d38e5e4 feat(scans): complete explain API — pipeline timing, docs, unit tests (M2, Task 5.4)
2e3f355 feat(scans): add GET /scans/{id}/explain explainability payload (M2, Task 5.3)
253bcfc M2 Task5.2: Grad-CAM explainability wired into detection + scan pipeline
00dfdde M2 Task5.1: Grad-CAM core module + storage read
```

## 10. Files (Task 5)

```
backend/app/ai/gradcam.py            backend/app/ai/types.py              (new)
backend/app/ai/classifiers.py        backend/app/services/detection.py
backend/app/services/scan_pipeline.py  backend/app/services/scans.py
backend/app/services/explain.py      (new)
backend/app/services/storage.py      backend/app/schemas/scan.py
backend/app/api/v1/endpoints/scans.py
backend/tests/test_gradcam.py        (new)   backend/tests/test_storage.py
backend/tests/test_detection.py      backend/tests/test_scan_pipeline.py
backend/tests/test_scan_api.py       backend/tests/test_explain_api.py    (new)
backend/tests/test_explain_service.py (new)  backend/tests/test_openapi_explain.py (new)
backend/tests/conftest.py
```

---

**Next:** M2 Task 6 (offline queue/sync) — awaiting approval.
