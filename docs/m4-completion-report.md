# Milestone 4 Completion Report — Marketplace & Farmer Community

**Milestone:** M4 · **Tag:** `v0.4.0-m4` · **Date:** 2026-08-09
**Branch:** `main` · **Status:** ✅ Complete

---

## 1. Milestone Summary

Milestone 4 turned NeuroPlant AI from a crop-care platform into a
**complete farming marketplace and farmer community**. Six task groups built the
full lifecycle — from a farmer listing produce and a shop selling inputs, to a
buyer browsing, saving, reviewing and messaging the seller:

| Task | Scope | Delivered |
|---|---|---|
| M4 T1 | Marketplace backend foundation | `CropListing` + `Product` models, vocabularies, layered `MarketplaceService` (browse/search/detail/CRUD), `/marketplace` router |
| M4 T2 | Farmer crop listings | Dashboard create/edit/delete/archive/stats, multi-photo uploader, listing form |
| M4 T3 | Buyer marketplace | Storefront browse (server-side search/filter/sort/pagination), listing detail with gallery + farmer block |
| M4 T4 | Seller portal + public product market | Shop profile, product catalog CRUD/stats, public `/marketplace/products` market + detail |
| M4 T5 | Buyer↔seller messaging | Conversations + messages store, Contact-Seller, inbox + thread UI, unread/read/close lifecycle |
| M4 T6 | Marketplace trust | Favourites (saved items) + reviews & ratings with live seller reputation |

Every gate is green: **407 backend tests** (1 skipped, **79% coverage**), **258
frontend tests** (39 files), clean Ruff / MyPy / ESLint / TypeScript, a
successful production build with PWA artifacts, a verified OpenAPI 3.1 spec
(**64 paths, 80 operations**), a single Alembic head with the dev DB current,
and a live **100/100 end-to-end smoke journey** covering every feature area and
security case in one script (`backend/scripts/m4_smoke_journey.py`).

---

## 2. Architecture Overview

```
┌───────────────────────────── Frontend (React / Vite / TS) ──────────────────────────────┐
│  M4 pages    marketplace-dashboard · marketplace-listing-form · marketplace-buy ·       │
│              marketplace-listing-detail · seller-dashboard · product-market-browse ·    │
│              product-market-detail · messages-list · messages-detail ·                  │
│              marketplace-favorites · my-reviews                                         │
│  Components  listing-card/grid · listing-gallery + lightbox · product-card/grid ·       │
│              filter-bars · pagination · stats-cards · image-uploader · shop-profile-    │
│              form · favourite-button · star-rating · rating-summary · review-card ·     │
│              review-form · review-section · copy-link-button · availability-badge       │
│  Data flow   TanStack React Query (per-surface keys) · server-backed favourite hook     │
│              with optimistic UI + in-flight guard · zustand auth · typed lib/api.ts     │
│  i18n        en / hi — 980 keys each, full parity (no gaps, no empty values)            │
│  Offline     PWA service worker + IndexedDB (M2) reused across all new pages            │
└───────────────────────────────────────┬─────────────────────────────────────────────────┘
                                         │  HTTPS / JSON (bearer auth, RBAC)
┌───────────────────────────────────────┴─────────────────── Backend (FastAPI / SQLAlchemy2) ─┐
│  Routers      marketplace (crops · crops/{id} · crops/search · crops/mine · crops/stats ·  │
│               crops/images · products · products/{id} · shop/register · shop/me ·          │
│               shop/products · shop/products/{id} · shop/image) · conversations ·           │
│               favorites · reviews — 26 routes total, all auth-required, role-gated         │
│  Services     MarketplaceService · MessagingService · FavoritesService · ReviewsService    │
│               — every business rule server-side (ownership, dedup, exactly-one target)    │
│  Data         4 new tables across migrations: marketplace listings + products (T1/T4),     │
│               conversations + messages (T5), favourites + reviews (T6)                    │
│  DB           SQLite (dev) / Postgres (prod) via Alembic · 12 revisions total, 4 added     │
│  Security     Reused M1 auth + RBAC (farmer/seller/admin) · enumeration-guard 404s         │
│               (scans/recovery/calendar pattern) · rate-limited messaging                   │
└──────────────────────────────────────────────────────────────────────────────────────────────┘
```

**Design principles carried through M4:**

- **Backend is the source of truth.** Ownership, RBAC, validation, exactly-one
  target rules, dedup, and the rating vocabulary all live server-side; the
  frontend transports intents and renders responses — no business logic
  duplicated on the client.
- **Enumeration-guard security.** Any resource that isn't the caller's (or
  missing) answers `404`, so ids can't be enumerated — the same convention as
  scans, recovery, calendar and messaging. Wrong-role callers are cut earlier
  by `403` RBAC.
- **Additive-only extension.** Every M4 backend change added tables/routes/fields
  without reshaping earlier ones (`archived` availability, organic product
  category, sort/filter windows, images, stats — each an approved additive
  extension).
- **Reuse mandate.** Reviews and favourites reuse the M4 Task 5 messaging item
  shapes (`ListingRefOut` / `ProductRefOut`); the seller reputation feeds the
  existing `FarmerSummaryOut` / `ShopSummaryOut`; the Pagination / ImageUploader
  / Lightbox / Badge components are shared, not duplicated.

---

## 3. Features Completed

### 3.1 Farmer crop listings (T1 + T2)
- `CropListing` model with the full sales vocabulary (`crop` categories,
  `units`, `availability` incl. `archived`), multi-image support, organic flag,
  harvest window and location.
- **Farmer dashboard** (`/marketplace`): create / edit / delete / mark-sold /
  mark-available / archive listings, `stats` cards (total / active / sold /
  archived), image uploader (validated JPEG/PNG/WebP, decoded server-side).

### 3.2 Buyer marketplace (T3)
- **Storefront** (`/marketplace/browse`): server-side search (`q`), category /
  organic / availability / price-range / location / harvest-window filters,
  sort (newest / oldest / price), pagination.
- **Listing detail** (`/marketplace/listings/:id`): gallery with lightbox,
  farmer block (name, verified, review-driven rating), copy-link, save, contact.

### 3.3 Seller portal + public product market (T4)
- **Seller portal** (`/marketplace/shop`): shop profile register / edit
  (description, hours, logo/banner), product catalog CRUD + stats, in/out of
  stock and archive lifecycle.
- **Public product market** (`/marketplace/products`): server-side
  search/filter/sort/pagination + product detail with shop block.

### 3.4 Buyer↔seller messaging (T5)
- `Conversation` + `Message` models (buyer, seller, optional listing/product
  context, status, `read_at`, `last_message_at`).
- **Create-or-reuse / reopen** — a second contact on the same item never stacks
  a duplicate thread; contacting a closed thread reopens it with history.
- **Contact Seller** on listing + product details; **inbox**
  (`/marketplace/messages`) with viewer-relative unread counts + previews;
  **thread UI** with mark-read, read receipts, close, and a locked composer on
  closed threads; **inquiries section** in the seller portal.

### 3.5 Favourites (T6)
- Server-backed saved items — a favourite targets **exactly one** crop listing
  *or* product (400 otherwise, idempotent re-save).
- `FavouriteButton` on both detail pages with optimistic toggle, in-flight
  guard and rollback; **saved-items page** (`/marketplace/favorites`).

### 3.6 Reviews & ratings + seller reputation (T6)
- One review per reviewer per item (409 on a second), self-review rejected
  (400), ownership-guarded edit/delete (404), rating 1–5 with title/content
  bounds and a whitespace-only guard (422).
- **Rating summary** (average, total, zero-filled 1–5 distribution) and
  `my_review` detection returned by the same list call.
- **Live seller reputation** — the review's `seller_id` is derived from the
  target, so a farmer's / shop's rating aggregates across all their listings and
  products and surfaces on `FarmerSummaryOut` / `ShopSummaryOut` everywhere.

---

## 4. Backend APIs (OpenAPI 3.1, 64 paths · 80 operations)

| Area | Path | Methods |
|---|---|---|
| Crop listings | `/api/v1/marketplace/crops` | GET (browse) · POST (create, farmer) |
|  | `/marketplace/crops/search` | GET (required `q`) |
|  | `/marketplace/crops/mine` · `/crops/stats` · `/crops/images` | GET (farmer) / GET (farmer) / POST (farmer) |
|  | `/marketplace/crops/{listing_id}` | GET (detail + farmer) · PATCH · DELETE |
| Products | `/api/v1/marketplace/products` · `/products/{product_id}` | GET (market) / GET (detail + shop) |
| Seller portal | `/marketplace/shop/register` · `/shop/me` · `/shop/image` | POST (seller) / GET · PATCH / POST |
|  | `/marketplace/shop/products` · `/shop/products/stats` · `/shop/products/images` | GET · POST / GET / POST |
|  | `/marketplace/shop/products/{product_id}` | PATCH · DELETE (seller) |
| Messaging | `/marketplace/conversations` | GET (inbox) · POST (create-or-reuse) |
|  | `/marketplace/conversations/{id}` · `/{id}/messages` · `/{id}/read` · `/{id}/close` | GET / POST / POST / POST |
| Favourites | `/marketplace/favorites` · `/favorites/status` · `/favorites/{favorite_id}` | GET · POST / GET / DELETE |
| Reviews | `/marketplace/reviews` · `/reviews/mine` | GET (list+summary+my_review) · POST / GET |
|  | `/marketplace/reviews/{review_id}` | PATCH · DELETE |

**M4 added 26 paths / 38 operations** on top of the M3 surface (37 paths / 42
operations). Every M4 endpoint requires authentication; crop management is
farmer/admin, the seller portal is seller/admin, and any authenticated role can
browse, save, review and message.

---

## 5. Database Migrations

Single Alembic head **`d2f4a6c8e0b1`** — 12 revisions total, 4 added in M4
(`alembic history` verified linear, no branches; `alembic upgrade head`
verified against a fresh DB):

| Revision | Added in | Tables / change |
|---|---|---|
| `a1c3e5b7d9f2` | T1 | `crop_listings`, `products` |
| `b7d3f5a9c1e4` | T4 | Seller-portal fields (description / hours / logo / banner, product extras) |
| `c2e4f6a8b0d2` | T5 | `marketplace_conversations`, `marketplace_messages` |
| `d2f4a6c8e0b1` | T6 | `marketplace_favourites`, `marketplace_reviews` |

Deletion safety: deleting a listing / product `SET NULL`s its favourite and
review references (honest "no longer available" markers); conversation history
keeps cached item refs.

---

## 6. Frontend Pages / Components

| Route | Page | Key components |
|---|---|---|
| `/marketplace` | `marketplace-dashboard.tsx` | `listing-card`, `filter-bar`, `stats-cards`, `image-uploader` |
| `/marketplace/listings/new`, `/listings/:id/edit` | `marketplace-listing-form.tsx` | `listing-form`, `image-uploader` |
| `/marketplace/browse` | `marketplace-buy.tsx` | `buyer-listing-grid`, `buyer-listing-card`, `buyer-filter-bar`, `pagination` |
| `/marketplace/listings/:listingId` | `marketplace-listing-detail.tsx` | `listing-gallery`, `lightbox`, `copy-link-button`, `favourite-button`, `review-section` |
| `/marketplace/shop` | `seller-dashboard.tsx` | `shop-profile-form`, `product-form`, `product-stats-cards`, `seller-product-filter-bar`, inquiries section |
| `/marketplace/products`, `/products/:id` | `product-market-browse.tsx`, `product-market-detail.tsx` | `product-listing-grid/card`, `product-listing-gallery`, `product-market-filter-bar` |
| `/marketplace/messages`, `/messages/:conversationId` | `messages-list.tsx`, `messages-detail.tsx` | conversation list + thread, `MessageBubble`/composer, unread badges |
| `/marketplace/favorites` | `marketplace-favorites.tsx` | saved-item cards (listing + product) + remove |
| `/marketplace/my-reviews` | `my-reviews.tsx` | `review-card`, `review-form` (inline edit) |
| — (embedded) | — | `star-rating`/`RatingInput`, `rating-summary`, `review-section`, `availability-badge` |

- **API client** — `src/lib/api.ts` gained the full marketplace surface
  (crops, products, shop, conversations, messages, favourites, reviews).
- **Types** — `src/types/marketplace.ts` (vocabularies + listing/product/
  farmer/shop/seller), `messages.ts`, `trust.ts` (favourites + reviews,
  `Review.listing` / `.product` typed as distinct ref shapes).
- **Accessibility / mobile** — `aria-pressed` favourite button with busy/error
  states, labelled review form + star input, `role="log"` message threads,
  unread `role="status"`, accessible pagination, stacked responsive layouts on
  every card grid and thread view, dark mode + reduced motion from M2 reused.
- **State** — React Query per-surface keys (`["favourites"]`,
  `["favourite-status", id…]`, `["reviews", listingId|productId, page]`,
  conversation keys) with optimistic mutations and prefix invalidation; the
  favourite hook guards a second in-flight toggle.

---

## 7. Security Model

| Case | Behaviour | Verified |
|---|---|---|
| Unauthorized requests | Every marketplace endpoint answers `401` without a token | smoke S1 |
| RBAC | Customer → crop/shop mutations `403`; farmer → seller portal `403` | smoke A12, S3 |
| Cross-user access | Second user's saved items / listing dashboard are empty | smoke S2 |
| Seller ownership | Same-role non-owner PATCH/DELETE answers `404` (enumeration guard) | smoke S3 |
| Product ownership | Second seller cannot patch/delete another seller's product (`404`) | smoke S3 |
| Review ownership | Other user cannot edit/delete a review (`404`) | smoke S4 |
| Favourite ownership | Other user cannot delete a favourite (`404`) | smoke S5 |
| IDOR attempts | Missing/foreign listing · product · thread · favourite → `404`/`405` | smoke S6 |
| Invalid input | Bad category/unit/sort → `422`; favourite/review/conversation with no or both targets → `400`; duplicate review → `409`; blank review → `422` | smoke S7 |
| Self-review | A farmer cannot rate their own listing (`400`) | smoke S7 |
| Thread isolation | Inboxes are participant-scoped — seller sees only their product threads, never the farmer's | smoke A8 |
| Rate limiting | Conversation create + message send use the shared token-bucket limiter | Task-5 tests |
| Input bounds | Rating 1–5, title ≤200, content ≤2000, message ≤2000, whitespace-only rejected | schema tests |

---

## 8. Test Results

### Backend — `pytest` (full suite)

**407 passed, 1 skipped** (408 collected), **0 failures**, **79% coverage**
(5294 statements, 1133 missed; no `--cov-fail-under` configured).

M4 feature files:

| File | Tests | Covers |
|---|---|---|
| `tests/test_marketplace.py` | 33 | listings CRUD, browse/search/filter/sort, seller shop + products, RBAC, ownership |
| `tests/test_messaging.py` | 15 | conversations, unread, mark-read, close/reopen, IDOR, rate limit |
| `tests/test_marketplace_trust.py` | 29 | favourites, reviews, dedup/self-review, ownership, rating summary, reputation |
| M1–M3 suites | 330 | full regression across auth, scans, treatment, soil, recovery, calendar, assistant |

### Frontend — `vitest`

**258 passed (39 files)**, clean `tsc -b --noEmit`, clean `eslint --max-warnings=0`.
M4 suites include `marketplace-dashboard`, `marketplace-listing-form`,
`marketplace-buy`, `marketplace-listing-detail`, `seller-portal`,
`product-market-browse/detail`, `messages`, `favourites` hook,
`marketplace-favorites`, `my-reviews`, `rating-summary`, `review-section` —
plus the full M1–M3 regression (scan, doctor, calendar, assistant, offline).

*Note: one pre-existing M2 pagination test (`scan-history`) flaked on its 5 s
default timeout under full 39-file parallel load; it passes in isolation and
was given a targeted per-test timeout bump — no assertion or gate weakened.*

### Live smoke journey — `backend/scripts/m4_smoke_journey.py`

**100 / 100 checks passed** against a live backend on a fresh migrated DB.
Walks all 12 feature areas (A1–A12) and all 7 security cases (S1–S7) in one
script: farmer listings → browse/filter → detail → seller portal → products →
favourites → reviews/reputation → conversations/messaging, with the full
unauthorized / RBAC / ownership / IDOR / invalid-input matrix. Self-cleaning
(registers fresh users; run against a disposable DB).

---

## 9. Coverage

**Overall backend: 79%** (informational). Strong modules: scans 96%, detection
93%, explain 97%, scan_pipeline 94%, config 97%, marketplace 69%, reviews 63%,
favourites 55%, messaging 52% — the marketplace read/validation layers are
behavior-covered by the 77 M4 feature tests and the live 100-check smoke
journey rather than exhaustively unit-tested. Frontend: 258 tests across 39
files; the M4 marketplace pages carry their own focused suites.

---

## 10. Build Results

| Gate | Result |
|---|---|
| `ruff check app tests` | ✅ All checks passed |
| `ruff format --check` | ✅ M4 files formatted (8 pre-existing M3 recovery/soil files flagged by the newer ruff 0.16.1 — left untouched per release policy, consistent with T1/T5 precedent) |
| `mypy app` | ✅ Success: no issues in 92 source files |
| `pip check` | ✅ No broken requirements |
| Frontend `tsc -b --noEmit` | ✅ Clean |
| Frontend `eslint . --max-warnings=0` | ✅ 0 warnings |
| Frontend `vite build` (production) | ✅ Built in ~8.4 s · PWA generated (`sw.js`, `manifest.webmanifest`, 11 precache entries, 983 KiB) — only the pre-existing >500 kB chunk warning |
| OpenAPI | ✅ 3.1.0 · 64 paths · 80 operations (verified against the app schema) |
| Alembic | ✅ Single head `d2f4a6c8e0b1` · linear 12-revision history · fresh-DB upgrade verified |
| i18n | ✅ en / hi **980 keys each**, zero gaps, zero empty values (programmatic cross-check) |

---

## 11. Known Limitations

1. **No order/transaction lifecycle** — the marketplace ends at messaging,
   favourites and reviews; a checkout/order system is future work (out of M4
   scope). A "verified purchase" badge would need it.
2. **No real-time messaging** — inbox/thread refresh on mount and after
   mutations, not on a socket; the model is future-ready for WS/SSE/email (see
   §13).
3. **Reviews are text + stars only** — no media, no revision history (edits
   overwrite in place).
4. **Favourites are a flat list** — no folders/tags/sort beyond newest-saved
   first.
5. **Real ML detection, push notifications and the 12 Indian languages are
   still M4-parallel / later work** (see §13) — the architecture seams exist.
6. **SQLite dev DB** (Postgres via the same Alembic migrations in production);
   **no Docker / Redis** — Celery runs eager, the rate limiter is in-process.
7. **Single JS chunk** still triggers Vite's >500 kB warning; code-splitting
   deferred.

---

## 12. Performance Notes

- **Server-side search/filter/sort/pagination** keeps browse grids cheap — the
  client never fetches full catalogs; `page_size` is capped server-side.
- **Aggregate reads are single-query**: the review list returns items +
  summary + `my_review` in one call; the inbox returns threads with batch
  `last_message` + unread aggregation (no per-thread round-trips); seller
  reputation is computed per detail request via `rating_summary`.
- **Optimistic React Query mutations** (favourite toggle, review edit/delete,
  message send) keep the UI instant with rollback on failure; query-key prefix
  invalidation avoids stale caches without polling.
- **Uploads are validated and bounded** (max 8 images, typed + size-checked,
  decoded to reject non-images) so image endpoints can't be abused as an
  unbounded store.

---

## 13. Future Work

- **Orders & payments** — Razorpay is the decided gateway; order history would
  unlock verified-purchase reviews and delivery tracking on top of the existing
  listing/product models.
- **Real-time notifications** — conversation rows already carry participants,
  status and unread; a WS/SSE/email transport is a change of transport, not
  model (documented in the M4 Task 5 report).
- **12 Indian languages** — the en/hi locale packs and `speechLocale` seam from
  M3.1/M3-T6 extend to full regional packs; marketplace strings are namespaced
  ready for it.
- **Real ML detection + push** — the M4-parallel tracks from M2/M3 carry
  forward; the marketplace surfaces (listings, shop, reputation) have no
  dependency on them.
- **Recommendation-aware marketplace** — the favourites union and seller
  ratings are ready inputs for the existing `recommendations` service.
- **Postgres + Docker in dev** — lift the SQLite fallback once available.

---

**Milestone 4 is complete and tagged `v0.4.0-m4`. Milestone 5 has not begun.**
