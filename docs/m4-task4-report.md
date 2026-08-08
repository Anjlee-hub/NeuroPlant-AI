# M4 Task 4 Report — Seller Portal

**Milestone:** M4 (Marketplace & Farmer Community) · **Task:** 4 of ? · **Date:** 2026-08-08
**Branch:** `main` · **Status:** ✅ Complete · **Commit:** `feat(m4): seller portal`

---

## 1. Summary

M4 Task 4 delivers the **seller portal**: a shop-profile dashboard at
`/marketplace/shop` where a seller registers their shop (name, address, phone,
delivery availability, description, opening hours, logo/banner), manages a full
product catalog (create / edit / archive / mark in/out of stock / delete), and
reads live statistics (total / active / out-of-stock / archived). Products flow
into the **public product market** at `/marketplace/products` — a browse page
with server-side search, category / organic / availability / price / brand
filters, sort, and pagination — plus a detail page at `/marketplace/products/:id`
with the seller's shop attached, the full photo gallery and lightbox, and buyer
actions (copy link, Contact Seller placeholder).

Everything respects the "reuse the existing backend / no duplicated business
logic" mandate:

- **The frontend is a pure client** over the marketplace APIs. Search, filter,
  sort and pagination on the public market happen **server-side**; the seller's
  dashboard filters client-side over the one list the API returns (their own
  products), with every mutation hitting the same PATCH/DELETE endpoints the
  market uses.
- **The backend additions are additive extensions** of the Task 1 marketplace
  module — new `products` lifecycle fields and shop-profile fields, new read/
  write endpoints — with RBAC (seller-only) enforced via the existing
  `require_roles` dependency, and no change to the farmer crop-listing surface.

---

## 2. Features Implemented

### Seller dashboard (`/marketplace/shop`)
- **Shop profile card + edit form** — register (auto-created on first visit
  via the seller's user), view, and edit the shop: name, address, phone,
  delivery availability toggle, description, opening hours, logo & banner.
- **Product catalog** — create / edit / delete products, archive them, and
  toggle availability `in_stock ↔ out_of_stock` right from the dashboard.
- **Live stats cards** — total products, active, out of stock, archived, all
  refreshed on every mutation.
- **Client-side search + filters** — text search, category, organic-only,
  availability, sort (newest / oldest / price).
- **Honest states** — loading skeletons, empty state with an Add-product CTA,
  filtered-empty state, and an error state with Retry.

### Public product market (`/marketplace/products`)
- **Server-side browse** — search over name / brand / description /
  manufacturer, filter by category / organic / availability / price window /
  brand, sort by newest / oldest / price, and page through results.
- **Product cards** — photo (or placeholder), name, brand, category, organic
  badge, price per unit, availability badge, link to detail.
- **Detail page (`/marketplace/products/:id`)** — full gallery + lightbox,
  every seller-entered field, the seller's shop (name, verified, rating,
  delivery availability), copy-link, and a **Contact Seller** placeholder for
  Task 5 messaging.

### Access control
- Public market requires an authenticated user (farmer/customer/seller).
- Shop/product management is **seller-only**; farmers are blocked (403).
- **Product isolation** — sellers only ever see/edit their own products; a
  second seller's product id returns 404 (enumeration guard).

---

## 3. Backend APIs

New / extended endpoints in `app/api/v1/endpoints/marketplace.py` (all under
`/api/v1/marketplace`; the existing crop-listing routes are untouched):

| Method | Path | Purpose |
|---|---|---|
| POST | `/shop/register` | Create the seller's shop profile (idempotent, returns existing) |
| GET | `/shop/me` | Read the authenticated seller's shop + product catalog |
| PATCH | `/shop/me` | Edit the shop profile (partial) |
| POST | `/shop/image` | Upload the shop logo/banner, return a storage URL |
| GET | `/shop/products` | List the seller's own products |
| POST | `/shop/products` | Create a product (201) |
| POST | `/shop/products/images` | Upload product photos |
| GET | `/shop/products/stats` | `{total, active, out_of_stock, archived}` |
| PATCH | `/shop/products/{product_id}` | Edit a product / set availability |
| DELETE | `/shop/products/{product_id}` | Delete a product (204) |
| GET | `/products` | Public product market — browse/search/filter/sort/page |
| GET | `/products/{product_id}` | Public product detail with seller shop attached |

RBAC is enforced by `SellerUser = Depends(require_roles(UserRole.SELLER,
UserRole.ADMIN))` on the shop/product management group; the public market uses
`CurrentUser` (any authenticated role). Ownership and enumeration guards are
enforced in `MarketplaceService` — a product belongs to one seller and is only
reachable through their own `seller_id`.

---

## 4. Database Changes

One additive Alembic migration, single head **`b7d3f5a9c1e4`**
(`revises a1c3e5b7d9f2`), `alembic upgrade head` verified against a fresh DB:

**`products`** (M4 Task 4 lifecycle extension):
- `organic` — boolean, NOT NULL, server default `0` (organic badge)
- `manufacturer` — varchar(200), nullable
- `usage_instructions` — text, nullable
- `availability` — varchar(20), NOT NULL, server default `'in_stock'`
- Indexes on `category` and `availability` (public-market filter columns)

**`seller_profiles`** (shop-profile extension):
- `description` — text, nullable
- `opening_hours` — varchar(200), nullable
- `logo_url` — varchar(500), nullable
- `banner_url` — varchar(500), nullable

All NOT NULL additions carry a server default so SQLite `ALTER ADD COLUMN` is
satisfied (same technique as the Task 1 delivery/rating columns).

---

## 5. Seller / Shop Architecture

- A seller is a `User` with `role = "seller"`. The shop lives in
  `SellerProfile` (one per user, `user_id` unique FK). `owner_name` is mirrored
  from the user record at register time.
- **Product isolation** is structural: every product row carries a `seller_id`
  FK to `users`, and every seller-scoped query in `MarketplaceService` is
  filtered by the authenticated user's id. The public market joins the product
  to its shop for the detail payload (`ProductDetailOut`).
- **Shop register is idempotent** — a seller who already has a shop gets their
  existing profile back (200), so the dashboard can call it safely on first
  load. `rating` is a read-only, review-driven field (0.0 until a later task),
  `verified` is not user-settable.
- **Frontend data flow** uses React Query with dedicated query keys
  (`SELLER_PRODUCTS_KEY`, `SELLER_STATS_KEY`, `SELLER_SHOP_KEY`); every
  successful mutation invalidates all three so the stats cards stay honest with
  the catalog.

---

## 6. Product Management

- **Create / edit** via `ProductForm` (used for both) — category
  (fertilizer/pesticide/seed/tool/organic), name, brand, price, unit,
  stock quantity, organic toggle, description, manufacturer, usage
  instructions, photos via the shared `ListingImageUploader`.
- **Availability lifecycle** — `in_stock` (default) ↔ `out_of_stock` toggles
  with a single PATCH; `archived` hides a product from the public feed (but not
  from the seller, and the detail URL still resolves) and can be set from the
  dashboard card. The archive/delete confirm dialogs are honest (`window.confirm`).
- **Statistics** — `GET /shop/products/stats` counts by availability and is
  invalidated after every mutation.

---

## 7. Frontend Pages / Components

| Route | Page | Components |
|---|---|---|
| `/marketplace/shop` | `seller-dashboard.tsx` | `ShopProfileForm`, `ProductForm`, `ProductCard`, `ProductStatsCards`, `SellerProductFilterBar`, `ui/switch`, `ui/textarea` |
| `/marketplace/products` | `product-market-browse.tsx` | `ProductListingGrid`, `ProductListingCard`, `ProductMarketFilterBar`, `Pagination` |
| `/marketplace/products/:id` | `product-market-detail.tsx` | `ProductListingGallery`, `ProductAvailabilityBadge`, `ui/badge`, `ui/card` |

- **API client** — `src/lib/api.ts` gained the seller + product-market methods
  (`getMyShop`, `updateShop`, `myProducts`, `createProduct`, `updateProduct`,
  `deleteProduct`, `getProductStats`, `browseProducts`, `getProduct`).
- **Types** — `src/types/marketplace.ts` added the `Product` / `ProductInput` /
  `ProductUpdate` / `ProductStats` / `SellerProfile` / `SellerUpdate` /
  `ProductDetail` types and the product category / unit / availability
  vocabularies, mirroring the backend schemas.
- **Router + nav** — two new static routes wired in `router.tsx`; `header.tsx`
  gained **My Shop** and **Buy Farm Inputs** nav entries.
- **Shared UI additions** — `ui/switch` (accessible checkbox-style toggle) and
  `ui/textarea`, both dependency-free (React + `cn` only).
- **Responsive** — pages and forms use `sm:`/`md:` breakpoints and
  `grid-cols-*`; cards stack on small screens.

### Type-safety cleanup (this checkpoint)
All remaining TypeScript errors were fixed with proper types (no `tsc` weakening):
- `shop-profile-form.tsx` — `Switch` `onChange` wired to the change event.
- `product-market-browse.tsx` — filter state typed as `ProductMarketFilters`,
  query built via the shared `toProductMarketQuery` mapper (single source for
  the string→number price conversion), retry button converted to the `Button`
  component.
- `seller-dashboard.tsx` — filter state typed as `SellerProductFilters`,
  missing `ProductCard` import added, and the dead create/update mutations
  (built for a non-existent `onSubmit` prop) removed in favour of the form's
  self-submitting `onSaved` contract.

### i18n cleanup (this checkpoint)
A static `t()` key cross-check surfaced real gaps; all fixed in **en + hi**
with full parity (no en-only / hi-only keys):
- Added `common.all` / `common.yes`, `productMarket.card.notOrganic`,
  `productMarket.detail.{seller, stockQuantity, copyLink, contactSeller}`, and
  the two new nav labels (`nav.sellerPortal`, `nav.productMarket`).
- Re-pointed code to existing keys where possible (`sellerPortal.addProduct`,
  `sellerPortal.profile.title`, `productMarket.filter.showFilters`/`clear`)
  instead of adding duplicates.

### Dependency fix (this checkpoint)
The working tree's accidental `npm install` had regenerated the lockfile and
**downgraded Tailwind `4.3.3 → 4.0.0`**, which broke the production build
inside `vite-plugin-pwa`. `package.json` + `package-lock.json` were restored to
the M3 baseline (the Task-4 code needs no new runtime deps) and reinstalled;
the build is green again (2395 modules, PWA 11 precache entries).

---

## 8. i18n

English + Hindi, full parity. New namespaces: `sellerPortal` (dashboard,
profile form, product form, stats, filter bar, product card) and `productMarket`
(browse, filter bar, product cards, detail, gallery, grid, pagination). The
existing `marketplaceBuy` (crop listings) is untouched. Verified by a script
that checks every static `t()` key resolves in `en.json` and that `en`/`hi`
have identical key structures.

---

## 9. Tests

**Backend** (`tests/test_marketplace.py`, +356 lines): seller shop profile
register/read/edit, product CRUD + lifecycle (availability toggles, archive),
stats, public browse/search/filter/sort/pagination, detail-with-shop, archived
hidden from feed, RBAC (farmer 403), and product-isolation / enumeration
guards.

**Frontend** (new `seller-portal.test.tsx`, 17 tests): dashboard auth gate,
profile + stats + catalog rendering, empty state, client-side search, stock
toggle, archive/delete with confirm (+ cancel path), error retry; browse auth
gate, grid rendering, server-side search params, no-results state; detail auth
gate, field + shop rendering, invalid-id error.

**Smoke journey** (`backend/scripts/m4_task4_smoke.py`, 42 checks, all passing
against a clean migrated DB): registers a seller + a farmer, walks the full
journey — shop register/read/edit → create ×3 → list/stats → availability
round-trip → edit → public browse/search/filter(organic/price/brand)/sort/
pagination → detail-with-shop → archive (hidden from feed, readable by URL,
visible when requested) → delete + enumeration/RBAC guards. Self-cleaning.

---

## 10. Quality-Gate Results

### Backend
| Gate | Result |
|---|---|
| `pytest` | **363 passed, 1 skipped** — 79% coverage |
| `ruff check` | ✅ All checks passed |
| `ruff format --check` | ✅ Task-4 files formatted; 8 pre-existing M3 files left untouched (ruff version drift, scoped out) |
| `mypy app` | ✅ Success: no issues in 81 source files |
| `pip check` | ✅ No broken requirements |

### Frontend
| Gate | Result |
|---|---|
| `vitest run` | ✅ **34 files / 215 tests passed** |
| `tsc -b --noEmit` | ✅ Clean |
| `eslint . --max-warnings=0` | ✅ 0 warnings |
| `vite build` (production) | ✅ Built in ~8s — 2395 modules, PWA `sw.js` + `manifest.webmanifest`, 11 precache entries |

---

## 11. Known Limitations

- **No images end-to-end in the smoke journey** — photo upload endpoints
  (`/shop/products/images`, `/shop/image`) are covered by the backend test
  suite; the smoke script exercises the product/availability/browse surface.
- **Contact Seller is a placeholder** — wired in the UI and i18n but not
  functional; M4 Task 5 messaging fills it in.
- **Shop rating is always 0** — reviews are a later task.
- **No pagination on the seller's own product list** — the seller list is one
  fetch (client-side filter); fine for realistic catalog sizes.
- **Dev DB had smoke-test rows cleaned up** after verification; a fresh
  `alembic upgrade head` DB is the supported baseline.

---

## 12. Future Marketplace Extensions

- **Messaging** (M4 Task 5) — buyer ↔ seller contact, replacing the placeholders.
- **Reviews & ratings** — drive the `rating` field that currently reads 0.
- **Orders / checkout** — availability and price fields are already in place.
- **Seller analytics** — views, enquiries, and stock-turnover beyond the four
  stats counts.
- **Shop pages** — a public `/marketplace/shops/:id` page linking all of a
  seller's products.
- **Delivery + location** — the shop already records delivery availability and
  an address; surfacing them to buyers at browse time is a natural follow-up.
