# M4 Task 6 Report — Marketplace Trust: Favourites + Reviews & Ratings

**Milestone:** M4 (Marketplace & Farmer Community) · **Task:** 6 of ? · **Date:** 2026-08-09
**Branch:** `main` · **Status:** ✅ Complete · **Commit:** `feat(m4): marketplace trust and favorites`

---

## 1. Summary

M4 Task 6 delivers the **marketplace trust layer**: saved items (favourites) and
seller/listing/product **ratings & reviews**. Together they give buyers a
"save for later" bucket and a reputation signal per seller, and they surface in
every relevant marketplace surface — crop-listing detail, product detail, a
saved-items page, a my-reviews page, and the seller portal.

The feature builds directly on the M4 Task 3/4 marketplace and the Task 5
messaging ref types, and honours the reuse mandate:

- **The backend is additive and is the source of truth.** Two new tables
  (`marketplace_favourites`, `marketplace_reviews`), a favourites service +
  endpoint module, a reviews service + endpoint module, and a single new
  migration. Ownership, RBAC, validation and the rating vocabulary all live
  server-side; the client only transports intents and renders responses.
- **A favourite targets exactly one item** — a crop listing *or* a product
  (never both), server-enforced. A review rates an item and, through it, its
  seller; aggregate reputation is computed server-side.
- **The frontend is a pure client** over the new APIs, reusing the existing
  marketplace page/component patterns and the M4 Task 5 `ConversationListingRef`
  / `ConversationProductRef` item shapes.

---

## 2. Features Implemented

### Favourites (saved items)
- **Model** — `MarketplaceFavorite` (user, one of `listing_id` / `product_id`,
  created_at), with a composite uniqueness guard so the same item can't be saved
  twice by the same user.
- **Toggle from any item detail** — a `FavouriteButton` on the crop-listing
  detail and product detail reads the saved state (`GET …/favorites/status`),
  then POSTs to save or DELETEs the favourite row to unsave. Optimistic UI with
  an in-flight guard: the button flips immediately, rolls back on error, and
  ignores clicks while a toggle is pending.
- **Saved-items page** (`/marketplace/favorites`) — lists every saved crop
  listing and product with a "View details" link into the item, a remove
  button per row, an empty state with a browse shortcut, and an error/retry
  state.

### Reviews & ratings
- **Model** — `MarketplaceReview` (reviewer, optional `listing_id` /
  `product_id`, `rating` 1–5, `title`, `content`, timestamps). One review per
  reviewer per target (a second post is rejected with 409 — the "edit instead"
  contract).
- **Rating summary** — the backend computes `average`, `total` and a
  zero-filled `distribution` over the 1–5 scale for any target or seller. The
  client reads the distribution via string keys (`"1"`…`"5"`), matching how JSON
  object keys serialize.
- **Reviews block** (`ReviewSection`) on listing and product detail — summary
  (average stars + count + full distribution bars), the paginated review list,
  a **"Your review"** card when the caller has already reviewed the item (with
  inline edit/delete, never duplicated in the list), and a "Write a review"
  form otherwise. Editing reuses the pre-filled form; a blank/empty review is
  blocked locally before any API call.
- **My reviews page** (`/marketplace/my-reviews`) — every review the caller has
  written, each linking back to the item it rates, with a "this item is no
  longer available" marker when the target has been deleted, plus inline
  edit/delete.
- **Seller reputation** — `FarmerSummary` (and the equivalent product-shop
  view) now carries `rating` + `review_count`, so the trust signal follows the
  seller across the marketplace rather than living only on a review page.

---

## 3. Backend APIs

New endpoint modules under `/api/v1` (all authentication-required):

**Favourites** — `app/api/v1/endpoints/favorites.py`:

| Method | Path | Purpose |
|---|---|---|
| GET | `/marketplace/favorites` | The caller's saved items (listing + product union) |
| GET | `/marketplace/favorites/status` | Saved state for one target (`listing_id` \| `product_id`) |
| POST | `/marketplace/favorites` | Save an item (201) |
| DELETE | `/marketplace/favorites/{favorite_id}` | Remove a saved item (204) |

**Reviews** — `app/api/v1/endpoints/reviews.py`:

| Method | Path | Purpose |
|---|---|---|
| GET | `/marketplace/reviews` | Paginated reviews for `listing_id` \| `product_id` \| `seller_id`, with `summary` and `my_review` |
| GET | `/marketplace/reviews/mine` | All reviews written by the caller |
| POST | `/marketplace/reviews` | Create a review (201; 409 if already reviewed) |
| PATCH | `/marketplace/reviews/{review_id}` | Edit own review (only sent fields change) |
| DELETE | `/marketplace/reviews/{review_id}` | Delete own review (204) |

Exactly one target scope is required for review list/create (400 otherwise);
unknown references return 400 (never a leak).

---

## 4. Security / Ownership Model

- **Authentication** — every endpoint requires `get_current_user`; any
  authenticated role may save items and review items they can see.
- **Ownership / IDOR guard** — favourites and reviews are reachable *only* by
  their owner: DELETE and PATCH on a row owned by another user return **404**
  (the platform's enumeration guard — same pattern as scans, recovery, calendar,
  messaging).
- **Self-review prevention** — the backend rejects reviewing your own
  listing/shop (400); review targets are resolved through the listing's farmer
  or the product's shop, and a 409 enforces one review per reviewer per target.
- **Input validation** — `rating` is clamped to 1–5, `title` ≤ 200 chars,
  `content` ≤ 2000 chars and non-empty (whitespace-only content rejected, 422).
- **Deletion safety** — deleting a listing or product nulls its favourite and
  review references (SET NULL), so history and saved rows degrade gracefully and
  the "no longer available" marker is honest.

---

## 5. Database Changes

One additive Alembic migration, single head **`d2f4a6c8e0b1`**
(`revises c2e4f6a8b0d2`), `alembic upgrade head` verified against the dev DB:

**`marketplace_favourites`**
- `id`, `user_id` (FK users, indexed), `created_at`
- `listing_id` (FK `crop_listings`, `SET NULL`, nullable) /
  `product_id` (FK `products`, `SET NULL`, nullable)
- Unique constraint `(user_id, listing_id)` and `(user_id, product_id)` — one
  save per item per user

**`marketplace_reviews`**
- `id`, `reviewer_id` (FK users, indexed), `seller_id` (FK users, indexed —
  the reputation subject)
- `listing_id` / `product_id` (FKs, `SET NULL`, nullable)
- `rating` (smallint, checked 1–5), `title` (varchar 200, nullable), `content`
  (Text), `created_at` / `updated_at`
- Partial unique index on `(reviewer_id, listing_id)` and `(reviewer_id,
  product_id)` — the "one review per reviewer per target" contract

---

## 6. Architecture

- **Service layer** — `FavoritesService` and `ReviewsService` own every business
  rule: exactly-one-target resolution (listing → its farmer, product → its
  shop), the reviewer-owns-only guard, one-review-per-target, rating clamping,
  the aggregate `summary` (average, total, zero-filled distribution across the
  full 1–5 scale), pagination, and `my_review` detection on the list endpoint so
  the detail page knows "Write a review" vs "Edit your review" without a second
  request.
- **Frontend data flow** uses React Query v5 with dedicated keys:
  - `statusKey(target)` = `["favourite-status", listingId ?? null, productId ?? null]`
  - `FAVOURITES_KEY` = `["favourites"]`
  - `reviewsQueryKey` = `["reviews", listingId ?? null, productId ?? null, page]`
  - The favourite hook flips state optimistically in `onMutate`, rolls back on
    failure, guards against a second in-flight toggle, and invalidates both the
    status and the saved-items list. Review mutations invalidate the review page
    prefix so the list, summary and `my_review` stay consistent with the server
    without polling.
- **Reuse** — the favourite/review payloads reuse the M4 Task 5
  `ConversationListingRef` / `ConversationProductRef` shapes (distinct types,
  not a union), so item links and deleted-item states behave identically across
  messaging, saved items and reviews.

---

## 7. Frontend Pages / Components

| Route | Page | Components |
|---|---|---|
| `/marketplace/favorites` | `marketplace-favorites.tsx` | `FavouriteCard`, `Pagination`, remove buttons |
| `/marketplace/my-reviews` | `my-reviews.tsx` | `ReviewCard`, `ReviewForm` (inline edit) |
| — (embedded in listing / product detail) | — | `FavouriteButton`, `ReviewSection` |
| — (embedded in `ReviewSection`) | — | `StarRating` / `RatingInput`, `RatingSummary`, `ReviewCard`, `ReviewForm` |

- **API client** — `src/lib/api.ts` gained the favourites + reviews methods
  (`listFavourites`, `favouriteStatus`, `addFavourite`, `removeFavourite`,
  `listReviews`, `listMyReviews`, `createReview`, `updateReview`,
  `deleteReview`).
- **Types** — `src/types/trust.ts` mirrors the backend schemas:
  `Favourite`, `FavouriteStatus`, `RatingSummary`, `RatingDistribution`, `Review`,
  `ReviewPage`, `ReviewCreateInput`, `ReviewUpdateInput`, `ReviewListParams`,
  and the client-side constants `RATING_MIN/MAX`, `REVIEW_TITLE_MAX_LENGTH`,
  `REVIEW_CONTENT_MAX_LENGTH`. `Review.listing` / `Review.product` are typed as
  the distinct ref shapes (`ConversationListingRef` / `ConversationProductRef`),
  matching the backend. `types/marketplace.ts` gained `rating` + `review_count`
  on `FarmerSummary`.
- **Hook** — `src/lib/favourites.ts` exposes the server-backed
  `useFavouriteStatus` hook (status query, add/remove mutations, optimistic
  flip, rollback, in-flight guard, key invalidation).
- **Router + nav** — two new routes (`/marketplace/favorites`,
  `/marketplace/my-reviews`) in `router.tsx`; `header.tsx` gained **Saved items**
  and **My reviews** nav entries.
- **Accessibility** — the favourite button is `aria-pressed` + `aria-busy` and
  announces "checking / saving / favourite error" states; the rating input is a
  keyboard-operable labelled star control; the review form fields are labelled
  (`Title`, `Your review`) with live error text; pagination reuses the shared
  `Pagination` component (`aria-label="Pagination"`).
- **Responsive** — saved-item cards and review rows stack on small screens; the
  rating-summary distribution bars and star counts wrap gracefully.

---

## 8. i18n

English + Hindi, full parity. New `favourites` and `reviews` namespaces cover the
saved-items page, the review summary/list/form/card, the "Your review" and
"Write a review" affordances, edit/delete actions, deleted-item markers, empty
states and error/retry text. `nav.favourites` / `nav.myReviews` were added to
both locales. Verified programmatically: **987 keys per locale, zero gaps in
either direction** (en → hi and hi → en). Existing marketplace labels
(`marketplaceBuy.actions.saving`, `checking`, `favouriteError`) are reused where
possible.

---

## 9. Tests

**Backend** (`tests/test_marketplace_trust.py`, 29 tests): unauthenticated 401s
across every favourites + reviews endpoint; save listing / save product /
favourite-status round-trips; duplicate save and status-after-save; favourite
list union + per-row remove (404 for another user's row); self-review rejection;
exactly-one-target enforcement (both / none / unknown → 400); create review
(with 201) and duplicate-review 409; rating clamp + length/empty/whitespace
validation; PATCH/DELETE ownership (edit or delete another user's review →
404); review list pagination + `summary` + `my_review`; reviews-by-seller
(reputation) aggregation; review → seller `rating`/`review_count` reflection;
deleted-item references nulled with the "no longer available" marker preserved.

**Frontend** (5 suites touched, 258 tests / 39 files total):
- `src/lib/__tests__/favourites.test.tsx` (9) — status load, saved-state
  reflection, listing-vs-product targeting, add, remove, optimistic flip via a
  pending promise, status error, toggle-failure message, in-flight second-toggle
  guard.
- `src/pages/__tests__/marketplace-favorites.test.tsx` (6) — auth gate, empty
  state with browse link, listing + product cards with correct detail hrefs,
  remove calls DELETE with the right row id, error/retry, per-row remove
  scoping.
- `src/pages/__tests__/my-reviews.test.tsx` (6) — auth gate, empty state, list
  with per-review back-links (distinct contents), deleted-item marker, delete,
  inline edit → submit.
- `src/components/__tests__/rating-summary.test.tsx` (2) — average/count + full
  distribution counts; partial string-keyed distribution renders with zero-filled
  buckets.
- `src/components/__tests__/review-section.test.tsx` (8) — loads reviews +
  summary, `product_id` targeting, "Your review" not duplicated in the list,
  write flow, local blank-content guard, inline edit, delete, pagination.
- `src/pages/__tests__/marketplace-listing-detail.test.tsx` — updated for the
  server-backed favourite toggle and the ratings & reviews block.

---

## 10. Quality-Gate Results

### Backend
| Gate | Result |
|---|---|
| `pytest` (venv) | ✅ **407 passed, 1 skipped** — 408 collected, 0 failures (29 new trust tests) |
| Coverage | ✅ 79% overall (`favorites.py` 55%, `reviews.py` 63%, `schemas/reviews.py` 89%) |
| Migration | ✅ Single head `d2f4a6c8e0b1`, applied to the dev DB via `alembic upgrade head` |

### Frontend
| Gate | Result |
|---|---|
| `vitest run` | ✅ **39 files / 258 tests passed** |
| `tsc -b --noEmit` | ✅ Clean |
| `eslint . --max-warnings=0` | ✅ 0 warnings |
| `vite build` (production) | ✅ Built in ~9s — only a pre-existing >500 kB chunk-size warning |

---

## 11. Known Limitations

- **No review media / verified-purchase badge** — reviews are text + stars only
  (per spec); a "verified buyer" signal would need order history, which is out
  of M4 scope.
- **No edit history** — updating a review overwrites content in place; there is
  no revision trail.
- **Favourites are a simple list** — no folders/tags or sort; the list is
  newest-saved-first by default.
- **Dev DB had verification rows cleaned up** after the test run; a fresh
  `alembic upgrade head` DB is the supported baseline.

---

## 12. Future Trust Architecture

- **Seller ratings on listings** — `FarmerSummary.rating` /
  `review_count` already flow through the API; surfacing them on browse cards
  is a frontend-only change when product management approves.
- **Verified-purchase reviews** — the review model's `listing_id`/`product_id`
  already link to the item; tying a review to a completed order (when orders
  land in a later milestone) is an additive flag + migration, no reshape.
- **Report / moderation** — an admin review-moderation surface can reuse the
  existing `seller_id`-scoped list endpoint and the ownership guard pattern.
- **Saved-item recommendations** — the favourites union query is a ready-made
  input for the recommendations service (`app/services/recommendations.py`).
