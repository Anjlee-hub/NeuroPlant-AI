# M4 Task 3 Report — Buyer Marketplace

**Milestone:** M4 (Marketplace & Farmer Community) · **Task:** 3 of ? · **Date:** 2026-08-07
**Branch:** `main` · **Status:** ✅ Complete · **Commit:** `feat(m4): buyer marketplace`

---

## 1. Summary

M4 Task 3 delivers the **buyer storefront**: browse every farm listing,
search by crop name, filter by category / organic / availability / price range /
harvest date / location, and sort by newest / oldest / price low-to-high /
price high-to-low. Each listing is a responsive card (photo, crop + variety,
category, organic badge, price per unit, quantity, harvest date, availability,
farmer location) linking to a detail page with a full photo gallery + lightbox,
every field the seller entered, and the buyer actions — save to favourites,
copy the listing link, and a Contact Farmer placeholder that Task 5's messaging
will fill in. Loading, empty, no-results and error states are all covered.

The "reuse the existing backend / no duplicated business logic" mandate is
honored end-to-end:

- **The frontend is a pure client** over the Task 1 browse/search endpoints.
  Search, filtering, sorting and pagination all happen **server-side**; the
  page holds at most one page of listings and never re-derives a business rule.
- **Two small additive backend extensions** (in the pattern approved in Task 2)
  give the storefront what Task 1's contract lacked: an `oldest` sort key and a
  `harvest_from` / `harvest_to` date window, plus a default that hides `archived`
  listings from the public feed (they mean "hidden from the market" per Task 2).
  No migration, no breaking change; every existing test is untouched.

## 2. Additive backend extension (approved pattern)

| Extension | Shape | Backward compatibility |
|-----------|-------|------------------------|
| Oldest sort | `sort=oldest` → `created_at asc, id asc` | One new value in `SORT_KEYS`; existing sorts unchanged |
| Harvest-date filter | `harvest_from` / `harvest_to` (YYYY-MM-DD, inclusive) on browse **and** search | New optional query params; a blank window still returns everything (dated or not) |
| Archived hidden by default | `browse_crops`/`search_crops` exclude `availability == archived` unless the caller passes `availability=archived` explicitly | Archived is a Task 2 value, so no Task 1 test observes it; the buyer's availability select can still reach retired listings deliberately |

All three live in the **one shared query builder** (`browse_crops` +
`_filter_conditions` + `_sort_clauses`), so browse and search semantics cannot
drift. `harvest_date` is a date column stored as naive datetime, so window
comparisons use `datetime.combine(day, time.min/max)` to stay inclusive.

## 3. Frontend data layer

### Types — `src/types/marketplace.ts`

Added the buyer-facing surface, mirroring `CropListingPageOut` /
`CropListingDetailOut`:

- `CropListingPage` (`items / total / page / page_size / pages`) — the
  paginated browse payload
- `CropListingDetail extends CropListing` with `FarmerSummary` (`id / name /
  verified`) — the detail payload
- `CropListingSort` and `CropListingQuery` — the browse/search params (all
  optional; the backend owns validation)

### API client — `src/lib/api.ts`

- `browseCrops(params)` → `GET /marketplace/crops` with a URLSearchParams
  builder that drops empty values (matching `listScans` exactly)
- `getCropListing(id)` return type widened to `CropListingDetail` (still
  structurally compatible with the farmer's edit page, which uses the same
  endpoint)

## 4. Internationalisation

A new `marketplaceBuy` i18n namespace in both `en.json` and `hi.json`
(structural parity verified — 64 keys each): auth gate, title/subtitle, error /
empty / no-results, sort labels, filter labels, card strings, detail labels,
gallery + lightbox strings and the action labels. Vocabulary labels (categories,
units, availability) are **reused** from the Task 2 `marketplace` namespace
rather than duplicated. `nav.marketplaceBuy` was added to the nav block.

## 5. Components — `src/components/marketplace/`

| Component | Responsibility |
|-----------|----------------|
| `BuyerFilterBar` | Search + sort + category / organic / availability selects; a collapsed "Filters" toggle reveals price min/max, harvest from/to and location. Reports changes up; the page owns state. `toBrowseQuery()` maps UI state → API params, dropping empties |
| `BuyerListingCard` | One shoppable card — the whole card is a link to the detail page; photo (lazy-loaded) or placeholder, crop + variety, category / organic / availability badges, price per unit, quantity, harvest date, location |
| `BuyerListingGrid` | Responsive 1 → 2 → 3 column grid |
| `Pagination` | Server-side page navigation: prev/next + a window of page buttons, `aria-current` on the live page, disabled at the ends, "Page X of Y" readout |
| `ListingGallery` | Main image with prev/next, a thumbnail strip, and an "Open photo" affordance; honest placeholder when a listing has no photos |
| `Lightbox` | Full-screen photo viewer: backdrop click + Escape close, arrow-key stepping, focus moved to Close on open, `role="dialog"` + `aria-modal` |
| `FavouriteButton` | Save / remove a listing — `aria-pressed`, filled-heart state. Backed by the localStorage hook only (below) |
| `CopyLinkButton` | Copies `window.location.href` via the async Clipboard API with a legacy fallback; shows "Link copied" for 2s |
| `ContactFarmerButton` | Deliberately **not** a chat — toggles "Messaging is coming soon." The farmer id is carried on `data-farmer-id` for the Task 5 thread |

### Favourites — `src/lib/favourites.ts`

`useFavourites()` is **architecture-ready with no backend**: a localStorage-backed
id set (`neuroplant.favourites`), kept in sync across tabs via the `storage`
event, exposing `isFavourite(id)` / `toggle(id)`. A future task swaps the storage
layer for a `POST /favourites/:listingId` call without touching the button.

## 6. Pages + routing

- **`/marketplace/browse` → `MarketplaceBuyPage`** — auth gate, filter bar,
  result count, grid, pagination. One `useQuery` keyed on the full filter
  query (`[...MARKETPLACE_BROWSE_KEY, query]`) so every filter/sort/page combo
  is cached independently; `keepPreviousData` keeps the grid on screen between
  fetches. Filter changes reset to page 1.
- **`/marketplace/listings/:listingId` → `MarketplaceListingDetailPage`** —
  auth gate, back link, gallery, crop/variety, price, quantity, harvest date,
  listed-on, description, location, availability + organic status, and a farmer
  block (name + verified badge) with the three buyer actions.

Routes coexist with the farmer's `/marketplace/listings/new` and
`/marketplace/listings/:listingId/edit` — React Router ranks static segments
above the dynamic `:listingId`, so the seller routes stay unambiguous.
`/marketplace` remains the seller dashboard; a "Buy" item was added to the nav
(`ShoppingBag`).

## 7. Performance

- **Server-side pagination** (existing `CropListingPageOut`); page navigation
  was chosen over infinite scroll for accessibility + testability.
- **Query caching** — the query key carries the whole filter query, so revisits
  to a filter combo (or back-navigation) are instant.
- **`keepPreviousData`** — no layout jump or flash of skeletons while
  filter/sort/page refetches land.
- **Lazy-loaded card images** so a large grid doesn't stall first paint.
- Search is deliberately **not** debounced — each keystroke queries the server,
  which is correct for a shared catalog and cheap at this scale (noted in
  limitations).

## 8. Accessibility

- Native `<select>` / `<input>` / `<button>` throughout (browser keyboard +
  screen-reader support); `sr-only` labels on every icon-only control.
- Lightbox is a focus-managed `role="dialog"` with `aria-modal`, Escape/arrow
  keys and backdrop-close.
- `aria-pressed` on the favourite toggle, `aria-current="page"` on the active
  pagination button, `aria-live="polite"` on the copy confirmation and result
  count, `role="status"` on the contact-farmer note.
- Mobile-first grids and stacked filters; visible focus rings on cards.

## 9. Testing

### Backend — `tests/test_marketplace.py` now **36 tests** (+3 for Task 3)

- `test_browse_sort_oldest` — `sort=oldest` returns creation order and
  `sort=newest` its reverse
- `test_browse_harvest_date_window` — `harvest_from`/`harvest_to` inclusive
  windows, un-dated listings excluded, reversed window empty
- `test_browse_hides_archived_unless_requested` — archived absent from the
  default feed but reachable with `?availability=archived`

### Frontend — **29 new tests** across four files

- `marketplace-buy.test.tsx` (9) — sign-in gate, cards + result count + detail
  links, server-side search-as-you-type, category filter, price sort,
  pagination forward/back, empty state, no-results state, error + retry
- `marketplace-listing-detail.test.tsx` (9) — sign-in gate, every field renders,
  gallery stepping + thumbnail jump, lightbox open + Escape close, no-photo
  placeholder, favourite toggle (incl. localStorage), copy-link to clipboard,
  contact-farmer note, error + retry
- `pagination.test.tsx` (6) — hidden on one page, next/prev callbacks, disabled
  ends, `aria-current`, "Page X of Y", no-op on current page
- `favourites.test.tsx` (5) — starts empty, toggle in/out persists, multiple
  ids, rehydrates from storage, ignores corrupt storage

## 10. Gates (all run)

| Gate | Result |
|------|--------|
| `pytest` (full backend suite) | **343 passed, 1 skipped** (was 340 / 1 skip) · **79% coverage** |
| `ruff check` | ✅ clean |
| `ruff format` (changed files) | ✅ clean |
| `mypy app` | ✅ no issues |
| `vitest run` (frontend) | ✅ **198 passed / 33 files** (was 169 / 29) |
| `tsc --noEmit` | ✅ clean |
| `eslint src` | ✅ clean |
| `vite build` | ✅ built (pre-existing chunk-size warning only) |

**Note (unchanged from Tasks 1–2):** the installed `ruff` (0.16.1) still flags
**8 pre-existing M3 files** (`recovery.py`, `soil.py`, `soil_seed_data.py` and
their tests) as needing a rewrap. Those files were untouched by Task 3 and were
not reformatted here so the commit stays scoped.

## 11. Files changed

```
backend/app/services/marketplace.py          SORT_OLDEST + harvest window + archived-hidden default
backend/app/api/v1/endpoints/marketplace.py  harvest_from/harvest_to on browse + search
backend/tests/test_marketplace.py            +3 Task 3 tests (now 36)

frontend/src/types/marketplace.ts            + CropListingPage, CropListingDetail, FarmerSummary,
                                             CropListingSort, CropListingQuery
frontend/src/lib/api.ts                      + browseCrops; getCropListing -> CropListingDetail
frontend/src/lib/favourites.ts               (new) useFavourites (localStorage, no backend)
frontend/src/lib/format.ts                   + formatDateOnly
frontend/src/locales/en.json / hi.json       + marketplaceBuy namespace + nav.marketplaceBuy
frontend/src/components/marketplace/         (new) buyer-filter-bar, buyer-listing-card,
                                             buyer-listing-grid, pagination, lightbox,
                                             listing-gallery, favourite-button, copy-link-button,
                                             contact-farmer-button
frontend/src/pages/marketplace-buy.tsx              (new) storefront
frontend/src/pages/marketplace-listing-detail.tsx   (new) detail + gallery + lightbox
frontend/src/app/router.tsx                  + /marketplace/browse + /marketplace/listings/:listingId
frontend/src/components/layout/header.tsx    + Buy nav item (ShoppingBag)
frontend/src/pages/__tests__/marketplace-buy.test.tsx            (new) 9 tests
frontend/src/pages/__tests__/marketplace-listing-detail.test.tsx (new) 9 tests
frontend/src/components/__tests__/pagination.test.tsx            (new) 6 tests
frontend/src/lib/__tests__/favourites.test.tsx                   (new) 5 tests
docs/m4-task3-report.md                      (this report)
```

## 12. Known limitations

- **Favourites are localStorage-only** — architecture ready for a backend, but
  not yet synced across devices or visible seller-side.
- **Contact Farmer is a placeholder** — "Messaging is coming soon." (M4 Task 5
  builds the real thread; the farmer id is already wired on the button).
- **Search is not debounced** — each keystroke fires a server request. Correct
  behavior for a shared catalog; a debounce would reduce low-bandwidth chatter.
- **Archived listings are hidden from the default feed** but still selectable
  via the availability filter — deliberate, per the "archived = hidden from the
  market" semantics.

## 13. Next

Task 4 (awaiting approval) — per the M4 plan.
