# M4 Task 2 Report — Farmer Crop Listings UI

**Milestone:** M4 (Marketplace & Farmer Community) · **Task:** 2 of ? · **Date:** 2026-08-07
**Branch:** `main` · **Status:** ✅ Complete · **Commit:** `feat(m4): farmer crop listings`

---

## 1. Summary

M4 Task 2 delivers the **farmer crop-listing dashboard**: the farmer's own
listings as cards with create / edit / delete / mark-sold / mark-available /
archive actions, a full create-edit form, multi-photo upload with previews and
validation, live stats counts, client-side filters + search, and an empty /
error / loading story — all responsive and mobile-first.

The requirement's "reuse the backend / no duplicated logic" mandate was honored
in both directions:

- The **frontend is a pure client** over the Task 1 API — it adds no business
  rules; the backend stays the single source of truth for ownership,
  validation and vocabulary.
- The **three backend additions Task 2 needs were delivered as an additive
  extension** (user-approved): `archived` joined the availability vocabulary,
  plus a stats endpoint and a multi-image upload endpoint. Nothing in the Task 1
  contract changed; every existing test is untouched.

## 2. Additive backend extension (approved)

Task 2's spec asked for "archive a listing" and "dashboard stats", which the
Task 1 model did not yet express. Rather than bend the frontend around a
missing capability, the backend was extended **backward-compatibly** — the
`available | limited | sold_out` vocabulary grew one value, no table or
migration changed, and Task 1's tests all still pass unchanged:

| Extension | Shape | Backward compatibility |
|-----------|-------|------------------------|
| Archive | `availability: "archived"` via the **existing** `PATCH /crops/{id}` | One new value in `AVAILABILITY`; existing values untouched |
| Stats | `GET /marketplace/crops/stats` → `CropListingStatsOut` (`total`/`active`/`sold`/`archived`) | New endpoint; `active = available + limited` keeps the semantics obvious |
| Image upload | `POST /marketplace/crops/images` (multipart, up to 8) → `ListingImagesOut` (`urls`) | New endpoint reusing the existing storage abstraction |

The upload path validates like the rest of the platform: count ≤ 8, content
type in an allow-list, ≤ 10 MB each, and **every file is decoded with PIL** so a
renamed text file can't sneak through as "an image". Files are stored under a
user-scoped `marketplace` subdir via `get_storage_service()` and returned as
`/media/...` URLs that go straight into a listing's `images` field. Invalid
uploads answer `422` (`ListingImageUploadError` mapped in `app/main.py`).

## 3. Frontend data layer

### Types — `src/types/marketplace.ts`

Mirrors the backend schemas with no duplicated logic: `CropListing`,
`CropListingInput`, `CropListingUpdate` (partial), `CropListingStats`,
`ListingImagesResult`, and the vocabularies (`CropCategory`, `CropUnit`,
`CropAvailability`). The availability union includes `archived` (the additive
extension).

### API client — `src/lib/api.ts`

Seven typed methods on the existing `api` client, following the scan/calendar
patterns exactly:

- `myCropListings()` → `GET /marketplace/crops/mine`
- `getCropListingStats()` → `GET /marketplace/crops/stats`
- `getCropListing(id)` → `GET /marketplace/crops/{id}`
- `createCropListing(payload)` / `updateCropListing(id, payload)` → `POST` / `PATCH`
- `deleteCropListing(id)` → `DELETE`
- `uploadListingImages(files)` → multipart `POST /crops/images` (builds the
  `FormData`, so the request helper's multipart branch sets no Content-Type)

## 4. Internationalisation

A new `marketplace` i18n namespace in both `en.json` and `hi.json` (parity
verified structurally) covering the dashboard, stats labels, availability
labels, categories, units, the form fields, uploader strings and action
confirmations. `nav.marketplace` already existed and is reused.

## 5. Components — `src/components/marketplace/`

| Component | Responsibility |
|-----------|----------------|
| `AvailabilityBadge` | Single source of truth for availability colors (success / secondary / destructive / outline-archived) |
| `StatsCards` | The four counts straight from the stats endpoint — never a client re-count |
| `FilterBar` | Search + status / category / organic / listed-date controls; reports changes to the page-owned state |
| `ListingCard` | One listing: photo or placeholder, crop + variety, category / organic / availability badges, price-per-unit, quantity, location; contextual actions (mark sold / available, archive, edit, delete) |
| `ListingImageUploader` | Multi-photo pick → client validation (≤ 8, JPEG/PNG/WebP, ≤ 10 MB) → batch upload → previews with remove, persisted URL list reported up |
| `ListingForm` | Create / edit form with every backend field, client-side required-field validation, saving + error states |

## 6. Pages + routing

- **`/marketplace` → `MarketplaceDashboardPage`** (replaces the ComingSoon
  placeholder). Header + "New listing" CTA, stats cards, filter bar, listing
  cards. Two queries feed it (`myCropListings`, `getCropListingStats`); the
  four mutations (mark-sold / mark-available / archive / delete) invalidate
  both on success so counts stay honest. Delete and archive confirm first.
- **`/marketplace/listings/new` and `/marketplace/listings/:listingId/edit` →
  `MarketplaceListingFormPage`** — one page for both modes; edit mode fetches
  the listing and seeds the form. Saving invalidates the dashboard keys and
  navigates back.

Filters are client-side over the farmer's own list (status, category, organic,
listed-date windows today/7d/30d, plus a case-insensitive search over
name/variety/description/location). This is presentation, not business logic —
the backend still owns every rule.

## 7. Testing

### Backend — `tests/test_marketplace.py` now **33 tests** (+8 for Task 2)

- `test_farmer_status_transitions` — available → sold → available → archived
  through the same PATCH endpoint
- `test_listing_stats_counts` — four seeded listings → `total 4 / active 2 /
  sold 1 / archived 1`
- `test_stats_require_farmer_role` — customers/others get 403
- `test_listing_image_upload` / `..._multiple` — PNG round-trip → `/media/*.png`
  URLs
- `test_listing_image_upload_rejects_non_image` / `..._bad_content_type` /
  `..._too_many` — 422s for text-as-image, wrong MIME, and a 9-image batch

### Frontend — **23 new tests** across three files

- `marketplace-dashboard.test.tsx` (12) — sign-in gate, stats + cards render,
  empty state with CTA, search narrows, status filter, mark sold / available,
  archive (confirm + cancel), delete (confirm + cancel), error + retry
- `listing-form.test.tsx` (5) — create submits the full payload, edit seeds +
  PATCHes, required-field block, server-error surface, cancel
- `image-uploader.test.tsx` (6) — persisted-URL render + removal, batch upload
  reporting, > 8 reject, > 10 MB reject, non-image reject (via `fireEvent`
  since `userEvent.upload` filters by the input's `accept` — the same "pick all
  files" path mobile browsers allow), 8-image cap hides the add tile

## 8. Gates (all run)

| Gate | Result |
|------|--------|
| `pytest` (full backend suite) | **340 passed, 1 skipped** (was 332 / 1 skip) · **79% coverage** |
| `ruff check app tests` | ✅ clean |
| `ruff format` (changed files) | ✅ clean (6 changed files) |
| `mypy app` | ✅ no issues (81 source files) |
| `vitest run` (frontend) | ✅ **169 passed / 29 files** (was 146 / 26) |
| `npm run lint` | ✅ clean (`eslint . --max-warnings=0`) |
| `npm run typecheck` | ✅ clean (`tsc -b --noEmit`) |
| `npm run build` | ✅ built (chunk-size warning is pre-existing) |

**Note (unchanged from Task 1):** the installed `ruff` (0.16.1) still flags
**8 pre-existing M3 files** (`recovery.py`, `soil.py`, `soil_seed_data.py` and
their tests) as needing a rewrap. Those files were untouched by Task 2 and were
not reformatted here so the commit stays scoped; they can be swept in a later,
format-only commit.

## 9. Files changed

```
backend/app/models/marketplace.py          availability comment (+ archived), no column change
backend/app/schemas/marketplace.py         AVAILABILITY + archived; + CropListingStatsOut, ListingImagesOut
backend/app/services/marketplace.py        + my_listings_stats, upload_listing_images, ListingImageUploadError
backend/app/api/v1/endpoints/marketplace.py  + GET /crops/stats, POST /crops/images
backend/app/main.py                        + ListingImageUploadError → 422
backend/tests/test_marketplace.py          +8 Task 2 tests (now 33)

frontend/src/types/marketplace.ts          (new) domain types + vocabularies
frontend/src/lib/api.ts                    +7 marketplace methods
frontend/src/locales/en.json               + marketplace namespace
frontend/src/locales/hi.json               + marketplace namespace (parity)
frontend/src/components/marketplace/       (new) availability-badge, stats-cards, filter-bar,
                                           listing-card, image-uploader, listing-form
frontend/src/pages/marketplace-dashboard.tsx       (new) dashboard
frontend/src/pages/marketplace-listing-form.tsx    (new) create / edit page
frontend/src/app/router.tsx                /marketplace → dashboard; + new/edit routes
frontend/src/pages/__tests__/marketplace-dashboard.test.tsx      (new) 12 tests
frontend/src/components/__tests__/listing-form.test.tsx          (new) 5 tests
frontend/src/components/__tests__/image-uploader.test.tsx        (new) 6 tests
docs/m4-task2-report.md                    (this report)
```

## 10. Next

Task 3 (awaiting approval) — per the M4 plan.
