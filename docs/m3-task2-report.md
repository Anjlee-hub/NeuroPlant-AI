# M3 Task 2 Completion Report — Treatment Recommendation UI

**Milestone:** M3 · **Task:** 2 · **Status:** Implemented — awaiting approval
**Branch:** `main` · **Date:** 2026-08-05

---

## 1. Overview

Task 2 integrates the **Treatment Recommendation Engine** (built in M3 Task 1) into the frontend. When a scan finishes (or a historical scan is opened from Scan History), the app fetches `GET /scans/{id}/recommendations` and renders a complete, farmer-friendly care plan.

The UI consumes the backend API exclusively — **no treatments are hardcoded**. Every section, icon, label, and safety warning comes from the seeded catalog data.

---

## 2. Features Implemented

### 2.1 API Client + Types (`src/lib/api.ts`, `src/types/recommendation.ts`)

- **New TS types** mirroring `DiseaseRecommendationOut` (backend `schemas/recommendation.py`):
  - `HomemadeRemedy`, `OrganicRemedy`, `ChemicalRecommendation` — structured item shapes
  - `RecommendationDisease` — disease context with crop name
  - `DiseaseRecommendation` — the full self-contained payload
- **New API method** `api.getScanRecommendations(scanId)` → `GET /scans/{id}/recommendations` (auth-gated, same refresh/retry logic as other endpoints).

### 2.2 Core UI Component — `RecommendationsPanel` (`src/components/treatment/recommendations.tsx`)

Single entry component that owns the query and renders all four states:
- **Loading** — skeleton cards (respects `prefers-reduced-motion`)
- **Empty (404)** — `StateCard` with sprout icon, friendly copy, no retry
- **Error** — `StateCard` with alert icon, retry button
- **Success** — delegates to `RecommendationsView`

### 2.3 Care Plan Renderer — `RecommendationsView`

**Header card** (disease + crop context, overview, cause, spread mechanism, symptoms grid).

**12 expandable category cards** (accordion pattern, keyboard-accessible, `aria-expanded`/`aria-controls`):
| Section | Icon | Source Field | Notes |
|---------|------|--------------|-------|
| Homemade Remedies | `Home` | `homemade_remedies[]` | Ingredients as chips, preparation, frequency |
| Organic Remedies | `Sprout` | `organic_remedies[]` | Application + frequency |
| Chemical Recommendations | `FlaskConical` | `chemical_recommendations[]` | **Safety precautions highlighted in amber warning box** |
| Fertilizer | `Flower2` | `fertilizer` | Text guidance |
| Watering | `Droplets` | `watering` | Text guidance |
| Sunlight | `Sun` | `sunlight` | Text guidance |
| Temperature | `ThermometerSun` | `temperature` | Text guidance |
| Humidity | `CloudRain` | `humidity` | Text guidance |
| Prevention Tips | `ShieldCheck` | `prevention_tips[]` | Bullet list |
| Recovery Timeline | `CalendarDays` | `recovery_timeline` | Text guidance |
| Isolation | `Ban` | `isolation` | Text guidance |
| Monitoring Advice | `Eye` | `monitoring_advice[]` | Bullet list |

**Behavior:**
- Default open: Homemade, Organic, Chemical (treatment actions first).
- `Expand all / Collapse all` toggle in header.
- Every section forced open under `@media print` so a printed report always shows the full plan.

### 2.4 Page Integration

| Page | Route | Integration Point |
|------|-------|-------------------|
| Scan Crop (live result) | `/detect` (phase `"result"`) | `ResultView` → `<RecommendationsPanel scanId={scan.id} />` after AI explanation |
| Scan Detail (history) | `/scans/:scanId` | Details column → `<RecommendationsPanel scanId={id} />` after AI explanation |

Navigation chrome (back link, copy/share buttons, download heatmap) + `print:hidden` so the print output is a clean care plan.

### 2.5 i18n — English + Hindi

All user-visible strings added under a new `"treatment"` top-level key in:
- `src/locales/en.json`
- `src/locales/hi.json`

Includes category vocabularies (`kitchen-ingredients`, `neem-oil`, `fungicide`, …) so badges translate automatically via `t(\`treatment.homemade.categories.${category}\`)`.

### 2.6 Print-Friendly Styles (`src/styles/globals.css`)

New `@media print` block:
- Hides `header`, `footer`, `nav`, `button`, `.print:hidden`
- Forces `.print:block` sections open
- White background, black text, stripped shadows/rounded, brand colors mapped to dark green (`#166534`)
- `@page { margin: 16mm }` for comfortable printed reports

---

## 3. Adding a New Disease to the Frontend

**No frontend code changes needed.** The UI is entirely data-driven:
1. Add the disease to the backend catalog (`app/db/seed_data.py`).
2. Optionally add a curated plan to `RECOMMENDATIONS` in `app/db/recommendation_seed_data.py` (keyed by `(crop common_name, disease name)`).
3. Bump `RECOMMENDATION_VERSION` and run `python -m app.db.seed`.
4. The new plan appears automatically in the app the next time a scan for that disease is opened.

---

## 4. Testing & Gates

### Frontend
- **TypeScript:** `npm run typecheck` — ✅ clean
- **ESLint:** `npm run lint` — ✅ clean
- **Vitest:** `npm run test` — **63 passed** (13 test files, no new test file added; existing tests still pass)
- **Build:** `npm run build` — ✅ production bundle (2345 modules, CSS warnings for `print:` pseudo-class are expected non-issues)

### Backend (regression check)
- **pytest:** `232 passed, 1 skipped` (85% coverage)
- **Ruff:** ✅ clean
- **MyPy:** ✅ clean (56 files)

---

## 5. Files Changed / Added

| File | Status | Purpose |
|------|--------|---------|
| `src/types/recommendation.ts` | **NEW** | TS interfaces for the recommendation payload |
| `src/lib/api.ts` | Modified | Added `getScanRecommendations` + type import |
| `src/components/treatment/recommendations.tsx` | **NEW** | Core panel + view + 12-section cards (390 lines) |
| `src/pages/scan-crop.tsx` | Modified | Import + render panel in `ResultView`; `print:hidden` on actions |
| `src/pages/scan-detail.tsx` | Modified | Import + render panel after details; `print:hidden` on chrome |
| `src/locales/en.json` | Modified | ~130 new keys under `"treatment"` |
| `src/locales/hi.json` | Modified | Hindi translations for all new keys |
| `src/styles/globals.css` | Modified | `@media print` block for care-plan printing |

---

## 6. Screenshots / Visual Checklist

- [x] Mobile-first responsive layout (tested at 375px, 768px, 1280px)
- [x] Expandable cards with icons, smooth chevron rotation
- [x] Safety precautions in amber warning box (chemical section)
- [x] Friendly green brand palette throughout
- [x] Print preview shows only the care plan, no chrome
- [x] Empty state when no plan exists (404)
- [x] Loading skeletons while fetching
- [x] Error state with retry button
- [x] Hindi strings render correctly (language switcher tested)

---

## 7. Commit

```bash
git add -A
git commit -m "feat(m3): treatment recommendation UI"
```

**Next:** M3 Task 3 — awaiting user approval; do not begin unprompted.