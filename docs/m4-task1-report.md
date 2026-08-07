# M4 Task 1 Report — Marketplace Backend Foundation

**Milestone:** M4 (Marketplace & Farmer Community) · **Task:** 1 of ? · **Date:** 2026-08-07
**Branch:** `main` · **Status:** ✅ Complete · **Commit:** `feat(m4): marketplace backend foundation`

---

## 1. Summary

M4 Task 1 delivers the **backend foundation for the farmer marketplace**: a
`CropListing` surface where farmers offer produce for sale and any authenticated
user (customers included) browses, searches, filters and opens listings, plus a
**seller shop** surface where sellers register an agricultural shop and manage a
product catalog of fertilizers, pesticides, seeds and tools.

Everything follows the platform's established layering — models → schemas →
service → endpoint — with the service owning every business rule (including the
ownership guard that answers **404 for other users' rows**, the same
enumeration guard scans/recovery/calendar use) and the routers mapping pure HTTP
semantics.

## 2. Roles

The four roles the requirement lists already exist from M1 and are unchanged:
`farmer`, `customer`, `seller`, `admin` (plus `expert`), defined in
`app/models/base.py::UserRole` and enforced at registration. Task 1 is the
**first consumer of `require_roles`** (`app/api/v1/deps.py`), the RBAC
dependency added in M1 but previously unused:

| Role           | Marketplace capabilities                                     |
|----------------|--------------------------------------------------------------|
| `farmer`       | Create / update / delete / list own crop listings            |
| `customer`     | Browse / search / filter / view listing details (read-only)  |
| `seller`       | Register shop, add / edit products, view own shop            |
| `admin`        | Everything (RBAC gates include admin; moderation-ready)      |

## 3. Models

New module `app/models/marketplace.py` (+ `SellerProfile` extended in
`app/models/user.py`). Portable types only (String / JSON / Float / Boolean /
DateTime) so the same schema runs on PostgreSQL (prod) and SQLite (native dev);
enums are stored as strings with app-level (schema) validation.

### `CropListing` (`crop_listings`)

`id`, `farmer_id` → `users.id` (CASCADE, indexed), `crop_name`, `category`
(vegetable|fruit|grain|pulses|spice|other), `variety`, `quantity`, `unit`,
`price` (per unit), `description`, `images` (JSON list), `harvest_date`,
`organic`, `location`, `availability` (available|limited|sold_out),
`created_at`/`updated_at`. Indexed on the columns customers actually filter by:
`farmer_id`, `category`, `availability`.

### `Seller` — the shop is the existing `SellerProfile`, not a new table

The requirement's "Seller model" fields — shop name, owner, address, phone,
products, delivery availability, rating — map onto the **existing**
`SellerProfile` row that M1 already created for every `seller`-role user
(`shop_name`, `address`, `verified`, plus the linked `User` as *owner*). M4 T1
**extends** that row with the three missing fields instead of duplicating a
seller table:

- `phone` — shop contact line
- `delivery_available` — Boolean, default `False` (server default `0` so the
  NOT NULL column stays SQLite `ALTER ADD COLUMN`-compatible)
- `rating` — read-mostly Float, default `0.0` (review-driven; a review system
  in a later task will write it)

This honors "do not recreate completed work" and "no duplicated logic" — a
second `seller` table would duplicate `shop_name`/`address`/`verified`.

### `Product` (`products`)

`id`, `seller_id` → `users.id` (CASCADE, indexed — denormalized like
`RecoveryLog.user_id` so every product op reuses a direct ownership guard),
`name`, `category` (fertilizer|pesticide|seed|tool — the four supported
categories), `brand`, `description`, `price`, `unit`, `stock_quantity`,
`images`, `created_at`/`updated_at`.

## 4. Schemas

New module `app/schemas/marketplace.py` — boundary validation and the shared
vocabularies:

- `CropListingIn` / `CropListingUpdate` (partial) / `CropListingOut` /
  `CropListingDetailOut` (listing + `FarmerSummaryOut`) / `CropListingPageOut`
  (paginated envelope)
- `SellerRegister` / `SellerUpdate` / `SellerOut` (shop + owner + product list)
- `ProductIn` / `ProductUpdate` (partial) / `ProductOut`
- Vocabularies `CROP_CATEGORIES`, `PRODUCT_CATEGORIES`, `AVAILABILITY`, `UNITS`
  validated via regex patterns at the boundary (unknown values → 422).

All `*Update` models are `exclude_unset`-applied so partial edits change only
the fields sent (and `null` clears a field).

## 5. Service

New module `app/services/marketplace.py` — `MarketplaceService`, one class, no
duplicated logic. Browse and search share **one query builder**
(`_filter_conditions` + `_sort_clauses`) so their filter/sort semantics can't
drift. Pagination is bounded (`DEFAULT_PAGE_SIZE = 20`, `MAX_PAGE_SIZE = 100`,
clamped server-side).

| Method | Purpose |
|--------|---------|
| `create_listing` / `update_listing` / `delete_listing` | Farmer listing CRUD, owned by `user.id` |
| `my_listings` | Farmer's own listings, newest first |
| `browse_crops` | Paginated feed + filters + sort + optional search term |
| `listing_detail` | One listing with its farmer attached |
| `register_shop` | Fill in / refresh the seller's `SellerProfile` |
| `my_shop` / `shop` | Shop payload: profile + owner name + product catalog |
| `add_product` / `update_product` / `shop_products` | Seller product catalog CRUD |

Ownership: `_listing_for_farmer` / `_product_for_seller` scope queries by the
current user's id, so a missing **or another user's** row raises the domain
error → `404` (enumeration guard). Domain errors (`CropListingNotFoundError`,
`ProductNotFoundError`, `SellerShopNotFoundError`) are mapped to HTTP in
`app/main.py` alongside every other service error.

## 6. Endpoints

New module `app/api/v1/endpoints/marketplace.py`, prefix `/marketplace`
(registered in `app/api/v1/router.py`). RBAC via `require_roles`; read routes
are open to any authenticated user. Static paths (`/crops/mine`,
`/crops/search`) are declared before `/crops/{listing_id}` so FastAPI never
reads them as an id.

| Method & path                          | Role                | Description                              |
|----------------------------------------|---------------------|------------------------------------------|
| `GET  /marketplace/crops`              | any authenticated   | Browse + filter + sort, paginated        |
| `GET  /marketplace/crops/search`       | any authenticated   | Text search (name/variety/description/location) |
| `GET  /marketplace/crops/{id}`         | any authenticated   | Listing detail with farmer               |
| `GET  /marketplace/crops/mine`         | farmer / admin      | Farmer's own listings                    |
| `POST /marketplace/crops`              | farmer / admin      | Create listing                           |
| `PATCH /marketplace/crops/{id}`        | farmer / admin      | Partial edit (404 if not owner)          |
| `DELETE /marketplace/crops/{id}`       | farmer / admin      | Delete (404 if not owner)                |
| `POST /marketplace/shop/register`      | seller / admin      | Register / refresh shop                  |
| `GET  /marketplace/shop/me`            | seller / admin      | Own shop + products                      |
| `POST /marketplace/shop/products`      | seller / admin      | Add product                              |
| `PATCH /marketplace/shop/products/{id}`| seller / admin      | Partial edit (404 if not owner)          |

**Architecture note on repositories:** the codebase (M1–M3) deliberately has no
separate repository layer — services own queries directly against `AsyncSession`
and centralize all SQL. Adding a repository layer now would split that single
source of query logic into a second place, i.e. the very duplication the task
asks to avoid. Task 1 keeps the established *models → schemas → services →
endpoints* stack, which is modular and non-duplicated.

## 7. Database

Alembic migration **`a1c3e5b7d9f2_add_marketplace.py`** (single head; dev DB
upgraded and verified):
- `create_table crop_listings` (+ 3 indexes)
- `create_table products` (+ seller index)
- `add_column` to `seller_profiles`: `phone`, `delivery_available` (server
  default `0`), `rating` (server default `0`)

`alembic heads` → `a1c3e5b7d9f2 (head)`; dev DB is current at that head.

## 8. Testing

New `tests/test_marketplace.py` — **25 tests** covering:

- **RBAC**: customer can't create listings (403), non-seller can't register a
  shop (403 for farmer/customer/expert), unauthenticated can't browse (401),
  admin can create listings.
- **Farmer lifecycle**: create round-trip (all fields + ownership), list own
  (newest first), partial update (untouched fields preserved), delete (204 →
  detail 404), another farmer can't edit/delete (404), missing detail 404.
- **Customer surface**: pagination (total/pages/tail page), every filter
  (category, organic, availability, price range, location, empty result),
  sort asc/desc, search by name/variety/description/location + filter
  composition, empty search, missing `q` → 422, detail includes farmer.
- **Seller surface**: register shop, `shop/me` includes products, all four
  product categories, partial product update, another seller can't edit a
  product (404), products can be added before the shop profile is filled.
- **Validation**: bad category / unit / availability, negative price, zero
  quantity, empty name, negative stock → 422.
- **Service policy**: `page_size` clamped to `MAX_PAGE_SIZE`, invalid sort
  falls back to newest.

## 9. Gates (all run)

| Gate | Result |
|------|--------|
| `pytest` (full suite) | **332 passed, 1 skipped** (was 308 / 1 skip) · **79% coverage** (was 78%) |
| `ruff check app tests` | ✅ clean |
| `ruff format` (changed files) | ✅ clean |
| `mypy app` | ✅ no issues (81 source files) |
| Alembic | ✅ single head `a1c3e5b7d9f2`, dev DB current |
| OpenAPI | ✅ 8 new paths (46 total / 55 ops) |

**Note:** the installed `ruff` (0.16.1) is newer than the `>=0.6` floor used
during M3; its format rules now flag **8 pre-existing M3 files** (e.g.
`recovery.py`, `soil.py`, `soil_seed_data.py` and their tests) as needing a
rewrap. Those files were untouched by Task 1 and were not reformatted here so
the commit stays scoped to the marketplace; they can be swept in a later,
format-only commit.

## 10. Files changed

```
backend/app/models/marketplace.py            (new) CropListing + Product
backend/app/models/user.py                   SellerProfile + phone/delivery_available/rating
backend/app/models/__init__.py               export new models
backend/app/schemas/marketplace.py           (new) schemas + vocabularies
backend/app/services/marketplace.py          (new) MarketplaceService
backend/app/api/v1/endpoints/marketplace.py  (new) /marketplace router
backend/app/api/v1/router.py                 register marketplace router
backend/app/main.py                          marketplace error → HTTP mappings
backend/alembic/versions/a1c3e5b7d9f2_add_marketplace.py  (new) migration
backend/tests/test_marketplace.py            (new) 25 tests
docs/m4-task1-report.md                      (this report)
```

## 11. Next

Task 2 (awaiting approval) — frontend marketplace UI, or the next backend
surface per the M4 plan.
