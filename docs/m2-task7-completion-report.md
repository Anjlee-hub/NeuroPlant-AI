# M2 Task 7 Completion Report — Scan History, Details & Offline Sync UI

**Milestone:** M2 · **Task:** 7 (7.1–7.5) · **Status:** Implemented — awaiting approval
**Branch:** `main` · **Date:** 2026-08-05

---

## 1. Overview

Task 7 delivered the complete scan-facing frontend for M2: **Scan History**,
**Scan Details**, and the **Offline Queue** screens, followed by a cross-app UI
polish pass and a final verification. The three feature pages are wired to the
existing M2 backend over typed API clients — the queue reuses the Task 6
`POST /scans/sync` contract without duplicating reconciliation logic — and all
screens share a common design language (badges, state cards, skeletons,
motion, dark mode). Every gate is green: 54 frontend tests, 217 backend tests
(84% coverage, incl. 85 API-integration tests), clean Ruff/MyPy, clean lint,
and a successful production build. All work is committed on `main`; the
working tree is clean.

Sub-tasks: **7.1** Scan History UI → **7.2** Scan Details UI → **7.3** Offline
Queue UI → **7.4** UI polish → **7.5** Final verification (this report).

## 2. Features Implemented

### 7.1 — Scan History (`frontend/src/pages/scan-history.tsx`)
- **Filterable list** — search text, crop (catalog), disease, date range,
  confidence min/max, severity, sync status, part type; `Reset` restores
  defaults. Filters map to the backend `GET /scans` query params.
- **Sort + pagination** — created-at/confidence/disease-name × asc/desc;
  12-per-page grid with prev/next and 40px touch targets on mobile.
- **Status badges** — confidence (colored by band), severity, sync status and
  part type via the shared badge module.
- **States** — skeleton grid while loading, empty state (link to detect),
  error state with retry, sign-in-required state; cards fade in with a
  staggered entrance.

### 7.2 — Scan Details (`frontend/src/pages/scan-detail.tsx`)
- **Header** — disease name, crop, timestamp, confidence badge, copy/share
  actions (copy reports "Copied!").
- **Image gallery** — main image + media strip; a maximize overlay modal with
  zoom controls and download.
- **Details list** — part type, severity, stage, confidence level, provider,
  timings (`formatMs`), sync status.
- **AI explanation cards** — top-ranked predictions with per-disease
  confidence, and an "AI confidence" advice card that flags low-confidence
  results in amber and suggests a fresh scan.
- **States** — skeleton, error + retry (refetches scan + explain), not-found
  for unknown ids, sign-in-required.

### 7.3 — Offline Queue (`frontend/src/pages/offline-queue.tsx`)
- **Pending scans** — thumbnail, crop name (via catalog), timestamp, status
  badge (Pending/Syncing/Synced/Failed), retry count, error message.
- **Actions** — retry a failed entry, cancel a pending one, sync the whole
  queue, remove a single completed record, clear completed.
- **Sync UI** — progress bar (`role="progressbar"`) with live counts, a
  result summary banner (`created/replayed/failed`), an amber conflict notice
  for `duplicate_client_scan_id`, and an online/offline banner.
- **Local-first** — IndexedDB `syncQueue` + a new `completedQueue` store
  (DB v2) so "Synced" entries and "Remove/Clear completed" are real; the queue
  reloads on connectivity change or after any drain via `syncUi.version`.

### 7.4 — UI polish
- **Shared status badges** (`components/ui/status-badges.tsx`) — single source
  of truth for confidence/severity/sync colors; removed the duplicated
  variant helpers from the two scan pages.
- **Shared state card** (`components/ui/state-card.tsx`) — one component for
  the empty/error/sign-in-required cards across all feature pages.
- **Login ARIA tabs** — `aria-controls` + `tabpanel` + localized label +
  arrow-key navigation; localized the tablist label (`auth.loginMethod`).
- **Reduced motion** — `MotionConfig reducedMotion="user"` app-wide plus a CSS
  `prefers-reduced-motion` fallback; brand-tinted text selection.
- **Mobile touch targets** — pagination, retry, and clear-completed buttons
  bumped to 40px (`h-10 sm:h-9`).
- **Animations** — scan-history cards fade in with the same stagger as the
  queue screen.

### 7.5 — Final verification (this report)
- Added the two missing screen tests (**Home** dashboard, **Register**) so all
  six named screens have coverage.
- Fixed a heading-hierarchy gap on the landing page (feature titles were
  `div`s → proper `h3`s under the `h2` section header).
- Stubbed `IntersectionObserver` in the test setup so `motion`'s
  `whileInView` renders under jsdom.

## 3. Components Created

| Component | Purpose |
|---|---|
| `pages/scan-history.tsx` | Filterable, sortable, paginated scan list |
| `pages/scan-detail.tsx` | Full scan report + AI explanation + image viewer |
| `pages/offline-queue.tsx` | Pending/completed queue with sync + progress |
| `components/ui/status-badges.tsx` | `ConfidenceBadge` / `SeverityBadge` / `SyncBadge` + variant helpers |
| `components/ui/state-card.tsx` | Shared empty/error/auth-required card |
| `offline/scan-sync.ts` | "scan" sync handler (translates `POST /scans/sync` results) |
| `offline/sync-store.ts` | zustand drain state (progress, outcome, `version`) |
| `offline/db.ts` (v2) | Adds `completedQueue` store; `MAX_COMPLETED` trim |

## 4. API Integration

All calls go through the typed client (`frontend/src/lib/api.ts`, base
`/api/v1`, bearer token, single-flight refresh):

| Flow | Endpoint | Notes |
|---|---|---|
| Auth | `POST /auth/register`, `/auth/login`, `/auth/otp/*`, `/auth/mfa/*`, `/auth/logout`, `GET /auth/me` | session hydrate on boot; MFA challenge routing |
| Scan History | `GET /scans` | filters/sort/page params mirror backend |
| Scan Details | `GET /scans/{id}` | 404 → "not found" state |
| Explainability | `GET /scans/{id}/explain` | advice + top predictions |
| Offline sync | `POST /scans/sync` | idempotent batch; per-item `created \| replayed \| failed`; conflict code surfaced on failures |

The queue is **not** a second implementation of reconciliation: `replay` in
`offline/sync.ts` owns attempts/backoff (`MAX_ATTEMPTS`), and the "scan"
handler maps per-item outcomes to the queue UI (created → completed record,
replayed → completed record, failed → `lastError`, conflict → amber notice).

## 5. Test Summary

| Suite | Result |
|---|---|
| Frontend `vitest` | **54 passed** (10 files) |
| — Home / Register (added 7.5) | 2 / 3 |
| — Scan History | 7 |
| — Scan Details | 9 |
| — Offline Queue | 13 |
| — Scan sync handler | 4 |
| — Status badges | 6 |
| — Login / LanguageSwitcher / ThemeToggle | 4 / 3 / 3 |
| Backend `pytest` (full) | **217 passed, 1 skipped**, **84% coverage** |
| — API integration subset (auth, scans, history, sync, explain, catalog, health) | **85 passed** |
| `ruff check .` / `ruff format --check .` | clean / 72 files |
| `mypy app` | clean (51 source files) |
| Frontend `tsc -b --noEmit` | clean |
| Frontend ESLint (`--max-warnings=0`) | clean |
| Frontend `vite build` | **success** |

### Verification matrix (Task 7.5)

| # | Acceptance item | Evidence |
|---|---|---|
| 1 | Login screen | `login.test.tsx` (password/OTP, submit, MFA routing, error) |
| 2 | Registration screen | `register.test.tsx` (fields, role switch, submit, server error) |
| 3 | Dashboard (landing) | `home.test.tsx` (hero, CTAs, feature heading hierarchy) |
| 4 | Scan History | `scan-history.test.tsx` (list, filters, pagination, badges, states) |
| 5 | Scan Details | `scan-detail.test.tsx` (report, rankings, copy, modal, states) |
| 6 | Offline Queue | `offline-queue.test.tsx` (13: pending/failed/conflict, retry/cancel, sync-all summary, progress, offline banner, completed clear/remove, error+retry) |
| 7 | API integration | Backend integration subset (85) + mock-verified client calls per screen |
| 8 | Loading/empty/error/skeleton states | Asserted in scan-history, scan-detail, offline-queue tests |
| 9 | Accessibility | ARIA tabs, `aria-live`, `role="progressbar"`, reduced-motion, touch targets (Task 7.4); heading hierarchy fix (7.5) |

## 6. Known Limitations

1. **MFA, 404, and coming-soon screens** have no dedicated component tests;
   they are verified by code audit and the auth-flow tests (MFA routing) only.
2. **No live browser QA** — `NODE_ENV=production` is exported globally in this
   environment, so verification is automated tests + static code audit.
   Responsive/dark-mode are verified at the token/class level, not visually
   on-device.
3. **Single JS chunk** (~655 kB, 202 kB gzip) triggers Vite's >500 kB warning;
   all M2 screens are eager-imported. Code-splitting is deferred to a later
   milestone.
4. **Backend limits inherited from Task 6** — in-process rate limiter (per
   instance), globally-unique `client_scan_id` (single-owner), and sequential
   per-item sync inference (bounds SQLite dev contention).
5. **Offline queue is capped** at 100 completed records (trimmed oldest) and
   sync requires a live bearer token (an expired token fails the whole
   request, not per item).
6. **Reduced-motion** is honored by JS and CSS animations, but `whileInView`
   reveals still require an `IntersectionObserver` (stubbed in tests; real
   browsers are fine).

## 7. Performance Notes

- **Production build** — JS 655 kB (202 kB gzip), CSS 36 kB (7 kB gzip); PWA
  `generateSW` precaches 11 entries (~678 KiB).
- **Caching** — React Query defaults (stale 60s, retry 1, no refetch on focus);
  the crops catalog is cached 5 min; the offline queue refetches only on
  mutation, connectivity change, or a completed drain (`syncUi.version`).
- **Animation** — transform/opacity only (GPU-friendly), index-staggered with
  a capped delay, disabled under `prefers-reduced-motion`.
- **Local-first** — one IndexedDB read per queue mutation; `completedQueue`
  trims to 100; sync drain skips work while `navigator.onLine === false`.
- **Backend** — 84% coverage; sync batches resolve idempotency with a single
  `IN (...)` query; sequential inference keeps SQLite dev DB contention low.
