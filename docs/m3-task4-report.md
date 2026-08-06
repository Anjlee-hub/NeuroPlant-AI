# M3 Task 4 Completion Report — Crop Doctor Dashboard

**Milestone:** M3 · **Task:** 4 · **Status:** Implemented — awaiting approval
**Branch:** `main` · **Date:** 2026-08-06

---

## 1. Overview

Task 4 delivers the **Crop Doctor Dashboard** — a single, print-ready per-scan
page that consolidates the full care plan: a **Plant Overview** (what was
scanned and with what confidence), an **AI Diagnosis** (model explanation,
what the AI observed, the Grad-CAM heatmap and the top-5 predictions), the
**treatment plan** and **soil plan** (reused unchanged from M3 Tasks 1–3), and
a new **Crop Recovery Tracker** where the farmer records each treatment applied
and watches recovery progress over time.

The dashboard reuses the existing recommendation and soil engines — **no
treatment/soil logic is duplicated**. The only new backend surface is the
recovery tracker (model + policy service + ownership-guarded endpoints). The
whole page exports to a **PDF report** via the browser's print pipeline
(`window.print()` + print-only chrome), so it works offline and needs no
server-side rendering.

## 2. Features Implemented

### 2.1 Crop Recovery Tracker (backend)

**`app/models/recovery.py`** — `RecoveryLog`: one row per farmer-recorded
treatment (`scan_id` + `user_id` FKs with `ON DELETE CASCADE`, indexed on
`(scan_id, applied_at)`), storing `treatment_applied` (required), optional
`notes`, a `progress` observation (`worsening | no-change | improving |
recovered`), `applied_at`, plus the standard `TimestampMixin`.

**`app/services/recovery.py`** — `RecoveryTrackerService` resolves a
`RecoveryTrackerOut` for a scan and computes recovery **entirely from documented
policy constants** (mirroring the soil-health philosophy):

- **Recovery percentage** — starts from a severity-dependent baseline
  (`severe 10% / moderate 20% / low 30%`), gains `+15%` per logged treatment,
  and is adjusted by the latest trend (`worsening −10% / improving +10% /
  recovered +20%`), clamped to `0–1`.
- **Recovery status** — derived from the percentage (`recovered ≥95% ·
  improving ≥60% · on_track ≥35% · at_risk otherwise`).
- **Risk level** — severity-based (`severe→high · moderate→medium · low→low`),
  escalated one step when detection confidence is low (<55%).
- **Reminders seam** — the service docstring documents where a future reminder
  schedule (`applied_at`-based) and notification channel plug in; no fake
  reminder functionality is shipped.

**`app/schemas/recovery.py`** — `RecoveryLogIn` / `RecoveryLogUpdate` (partial
via `exclude_unset`) / `RecoveryLogOut`, a compact `RecoveryScanOut` summary
(crop name + model provenance resolved server-side), and `RecoveryTrackerOut`
(risk, percentage, status, timeline, totals).

**`app/api/v1/endpoints/recovery.py`** — all scan ownership-guarded through
`ScanService.get_for_user`:

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/v1/scans/{scan_id}/recovery` | Current tracker (percentage, status, risk, timeline) |
| POST | `/api/v1/scans/{scan_id}/recovery/logs` | Log a treatment (201) |
| PATCH | `/api/v1/scans/{scan_id}/recovery/logs/{log_id}` | Edit a log (partial update) |
| DELETE | `/api/v1/scans/{scan_id}/recovery/logs/{log_id}` | Remove a log (204) |

**`alembic/versions/d9e7f5b3c1a2_add_recovery_logs.py`** — creates the
`recovery_logs` table + indexes; applied to the dev DB.

### 2.2 Crop Doctor Dashboard (frontend)

- **`src/components/doctor/plant-overview.tsx`** — `PlantOverview`: crop,
  plant part (localized), disease, confidence / severity / risk badges, scan
  date, AI provider + model version. Missing fields fall back to a dash.
- **`src/components/doctor/ai-diagnosis.tsx`** — `AiDiagnosis`: the model's
  explanation, a "What the AI Observed" symptom list, the **Grad-CAM heatmap
  overlay** (with provider/timing caption), and the **top-5 predictions** with
  confidence bars. Graceful fallback when explainability data is absent.
- **`src/components/doctor/recovery-tracker.tsx`** — `RecoveryTrackerPanel` +
  `RecoveryTrackerView`: progress header (status badge, `role="progressbar"`
  with `aria-valuenow`, percentage, treatment count), an add/edit/delete
  treatment form (treatment name, optional progress, date and notes; inline
  delete confirmation), and the **treatment timeline**. Mutations invalidate the
  query so the percentage updates immediately.
- **`src/pages/scan-doctor.tsx`** — `ScanDoctorPage`: auth gate, five dashboard
  sections (overview → diagnosis → treatment → soil → recovery), a print-only
  report header, and the **Download PDF report** button. **Treatment and soil
  panels are the exact components from Tasks 1–3** (`RecommendationsPanel`,
  `SoilRecommendationsPanel`).
- **PDF report** — `window.print()` with `print:hidden` chrome (nav, header,
  footer, buttons) and a print-only branded report header; every accordion
  section is forced open under `print` so the report shows the full plan.
- **Routing** — new `scans/:scanId/doctor` route; `/doctor` now redirects to the
  scan list (the "coming soon" hub was stale now that the dashboard is live).
- **Entry points** — "Crop Doctor" buttons added to the scan result page
  (`scan-crop.tsx`) and scan detail (`scan-detail.tsx`).
- **i18n** — new `doctor` and `recovery` namespaces in `en.json`/`hi.json`
  (UI chrome localized; catalog content stays English).
- **Shared badge** — `RiskBadge` added to `ui/status-badges.tsx` (reused by the
  overview and tracker).

## 3. Test Results

### 3.1 Backend (`tests/test_recovery.py` — 14 new tests)
Policy unit tests (severity baseline, step-per-log, trend adjustment, clamping,
status thresholds, low-confidence risk escalation) and endpoint tests (auth
required, full tracker happy path, add-log updates percentage + timeline, 422
validation, partial update, delete, 404 for unknown/foreign scans, log-404-when-
not-on-this-scan, risk reflected in payload).

**Full backend suite:** `264 passed, 1 skipped` · coverage **85%** (was 250/84%).
Ruff: **All checks passed**. MyPy: **Success (65 files)**.

### 3.2 Frontend (4 new test files, 21 tests)
- **`recovery-tracker.test.tsx` (8)** — loading skeleton, error + retry, success
  state (status, progressbar value, timeline), empty timeline, add / edit /
  delete (with inline confirm) / cancel flows.
- **`plant-overview.test.tsx` (4)** — crop/part/disease/provenance, badges,
  risk-prop override, missing-field dashes.
- **`ai-diagnosis.test.tsx` (5)** — null fallback, explanation + observed
  symptoms, heatmap overlay, top-5 ranking, no-symptoms note.
- **`scan-doctor.test.tsx` (4)** — auth gate, full dashboard render, PDF via
  `window.print`, error + retry.

**Full frontend suite: `93 passed` (18 files)** (was 72/14).
TypeScript `tsc -b --noEmit`: **clean**. ESLint `--max-warnings=0`: **clean**.
Production `vite build`: **OK** (pre-existing chunk-size warning only).

## 4. Files Changed / Added

- **Backend (new):** `app/models/recovery.py`, `app/schemas/recovery.py`,
  `app/services/recovery.py`, `app/api/v1/endpoints/recovery.py`,
  `alembic/versions/d9e7f5b3c1a2_add_recovery_logs.py`,
  `tests/test_recovery.py`
- **Backend (modified):** `app/models/__init__.py`, `app/api/v1/router.py`,
  `app/main.py`
- **Frontend (new):** `src/types/recovery.ts`,
  `src/components/doctor/plant-overview.tsx`,
  `src/components/doctor/ai-diagnosis.tsx`,
  `src/components/doctor/recovery-tracker.tsx`, `src/pages/scan-doctor.tsx`,
  and their 4 test files
- **Frontend (modified):** `src/lib/api.ts`, `src/components/ui/status-badges.tsx`,
  `src/app/router.tsx`, `src/pages/scan-crop.tsx`, `src/pages/scan-detail.tsx`,
  `src/components/layout/header.tsx`, `src/components/layout/footer.tsx`,
  `src/locales/en.json`, `src/locales/hi.json`

## 5. Future-Ready Notes

- **Recovery reminders** — the next milestone can schedule notifications from
  `applied_at` without touching the tracker schema or API; the seam is
  documented in the service.
- **Recovery policy** is data as constants, so the percentage/status/risk
  formulas can be tuned or exposed as a config without schema changes.
- **Print-based PDF** means the report works fully offline (PWA) and requires no
  server-side document service.
- **Restart the dev backend** to pick up the new `/recovery` routes (started
  without `--reload`).

**Next:** M3 Task 5 — awaiting user approval; do not begin unprompted.
