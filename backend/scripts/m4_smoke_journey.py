"""M4 (Marketplace & Farmer Community) — full end-to-end API smoke journey.

Walks the *entire* M4 marketplace against a live backend, exercising every
feature area and the security model:

  A1 Farmer crop listings      A6 Product marketplace      S1 Unauthorized
  A2 Buyer marketplace         A7 Buyer↔seller convos      S2 Cross-user
  A3 Listing details           A8 Messaging                S3 Seller ownership
  A4 Seller portal             A9 Favourites               S4 Review ownership
  A5 Product management        A10 Reviews & ratings       S5 Favourite ownership
                               A11 Seller reputation       S6 IDOR attempts
                               A12 Auth / RBAC             S7 Invalid input

Each ``check`` names the area it proves (e.g. ``A1``, ``S6``), so the run is a
self-documenting verification report. Users are created with random phone
numbers, so the script is safe to run repeatedly against a disposable DB:

    DATABASE_URL=sqlite+aiosqlite:///./neuroplant-smoke.db \\
        ./.venv/Scripts/python.exe -m alembic upgrade head
    ./.venv/Scripts/python.exe scripts/m4_smoke_journey.py

Run against a live backend (start: uvicorn app.main:app --port 8001).
"""

import io
import sys
import uuid

import httpx
from PIL import Image

BASE = "http://127.0.0.1:8001"
API = f"{BASE}/api/v1"

# Windows consoles default to cp1252, which cannot print the em/en-dashes in the
# fixture payloads; force UTF-8 so failure details never crash the script.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

passed = []
failed = []


def check(name: str, cond: bool, detail: str = ""):
    if cond:
        passed.append(name)
        print(f"  ok  {name}")
    else:
        failed.append(name)
        print(f"  FAIL {name} — {detail}")


def _phone() -> str:
    return f"9{str(uuid.uuid4().int)[:9]}"


def _tiny_png() -> bytes:
    """A 1x1 PNG for the image-upload endpoints (valid, decodable)."""
    buf = io.BytesIO()
    Image.new("RGB", (1, 1), color=(42, 140, 60)).save(buf, format="PNG")
    return buf.getvalue()


def _register(client: httpx.Client, role: str, name: str):
    """Register a fresh user and return their auth headers."""
    r = client.post(
        "/auth/register",
        json={
            "phone": _phone(),
            "name": name,
            "role": role,
            "password": "secret123",
        },
    )
    assert r.status_code == 201, f"register {role} {name}: {r.status_code}: {r.text[:200]}"
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def main() -> None:
    client = httpx.Client(base_url=API, timeout=30)

    # ── Pre-flight ─────────────────────────────────────────────────────────
    r = client.get(f"{BASE}/ready")
    check("GET /ready (live server)", r.status_code == 200, r.text)

    # ══════════════════════════════════════════════════════════════════════
    # S1 Unauthorized + S7 Invalid input (no token) — auth is the outer gate
    # ══════════════════════════════════════════════════════════════════════
    r = client.get("/marketplace/crops")
    check("S1 browse crops without token → 401", r.status_code == 401, f"{r.status_code}")
    r = client.get("/marketplace/products")
    check("S1 browse products without token → 401", r.status_code == 401, f"{r.status_code}")
    r = client.get("/marketplace/crops/1")
    check("S1 listing detail without token → 401", r.status_code == 401, f"{r.status_code}")
    r = client.get("/marketplace/favorites")
    check("S1 favourites without token → 401", r.status_code == 401, f"{r.status_code}")
    r = client.get("/marketplace/reviews")
    check("S1 reviews without token → 401", r.status_code == 401, f"{r.status_code}")
    r = client.get("/marketplace/conversations")
    check("S1 conversations without token → 401", r.status_code == 401, f"{r.status_code}")

    # ══════════════════════════════════════════════════════════════════════
    # A12 Auth / RBAC — register the whole cast, then exercise role gates
    # ══════════════════════════════════════════════════════════════════════
    farmer = _register(client, "farmer", "Farmer Trust")
    farmer2 = _register(client, "farmer", "Farmer Other")
    seller = _register(client, "seller", "Seller Trust")
    buyer1 = _register(client, "customer", "Buyer One")
    buyer2 = _register(client, "customer", "Buyer Two")
    outsider = _register(client, "customer", "Outsider")

    r = client.get("/marketplace/shop/me", headers=farmer)
    check("A12 farmer blocked from seller portal → 403", r.status_code == 403, f"{r.status_code}")
    r = client.post("/marketplace/crops", json={}, headers=buyer1)
    check("A12 customer blocked from creating listings → 403", r.status_code == 403, f"{r.status_code}")
    r = client.post("/marketplace/shop/products", json={}, headers=buyer1)
    check("A12 customer blocked from creating products → 403", r.status_code == 403, f"{r.status_code}")
    r = client.get("/marketplace/crops/mine", headers=buyer1)
    check("A12 customer blocked from farmer dashboard → 403", r.status_code == 403, f"{r.status_code}")

    # ══════════════════════════════════════════════════════════════════════
    # A1 Farmer crop listings (+ A3 detail, A11 seller reputation seed)
    # ══════════════════════════════════════════════════════════════════════
    r = client.post(
        "/marketplace/crops",
        json={
            "crop_name": "Tomato",
            "category": "vegetable",
            "variety": "Desi",
            "quantity": 50,
            "unit": "kg",
            "price": 40,
            "description": "Farm fresh tomatoes from Nashik.",
            "location": "Nashik",
            "organic": True,
            "availability": "available",
            "harvest_date": "2026-07-15T00:00:00Z",
        },
        headers=farmer,
    )
    check("A1 create listing (201)", r.status_code == 201, f"{r.status_code}: {r.text[:200]}")
    listing_id = r.json()["id"]

    r = client.post(
        "/marketplace/crops",
        json={
            "crop_name": "Wheat",
            "category": "grain",
            "quantity": 100,
            "unit": "kg",
            "price": 30,
            "availability": "sold_out",
        },
        headers=farmer,
    )
    check("A1 create second listing (201)", r.status_code == 201, f"{r.status_code}: {r.text[:200]}")
    listing2_id = r.json()["id"]

    files = {"files": ("tomato.png", _tiny_png(), "image/png")}
    r = client.post("/marketplace/crops/images", files=files, headers=farmer)
    check("A1 upload listing image (200 urls)", r.status_code == 200 and r.json()["urls"], f"{r.text[:200]}")
    img_url = r.json()["urls"][0]

    r = client.patch(
        f"/marketplace/crops/{listing_id}",
        json={"price": 42, "images": [img_url], "availability": "limited"},
        headers=farmer,
    )
    check("A1 patch listing (200)", r.status_code == 200, f"{r.status_code}: {r.text[:200]}")
    check(
        "A1 patch persisted fields",
        r.json()["price"] == 42 and r.json()["images"] == [img_url] and r.json()["availability"] == "limited",
        r.json(),
    )

    r = client.get("/marketplace/crops/mine", headers=farmer)
    check("A1 farmer listing list = 2", r.status_code == 200 and len(r.json()) == 2, f"{r.status_code}: {r.text[:200]}")
    r = client.get("/marketplace/crops/stats", headers=farmer)
    check(
        "A1 listing stats (total 2, active 1, sold 1)",
        r.status_code == 200
        and r.json()["total"] == 2
        and r.json()["active"] == 1
        and r.json()["sold"] == 1,
        r.json(),
    )

    r = client.get(f"/marketplace/crops/{listing_id}", headers=buyer1)
    body = r.json()
    check("A3 listing detail (200)", r.status_code == 200 and body["id"] == listing_id, f"{r.status_code}")
    check(
        "A3 farmer summary present (name/verified/rating/review_count)",
        body["farmer"]["name"] == "Farmer Trust"
        and body["farmer"]["verified"] is False
        and body["farmer"]["rating"] == 0.0
        and body["farmer"]["review_count"] == 0,
        body["farmer"],
    )
    farmer_id = body["farmer"]["id"]

    # ══════════════════════════════════════════════════════════════════════
    # A2 Buyer marketplace — browse / search / filter / sort / pagination
    # ══════════════════════════════════════════════════════════════════════
    r = client.get("/marketplace/crops", headers=buyer1)
    check("A2 browse crops (200)", r.status_code == 200 and r.json()["total"] == 2, f"{r.status_code}: {r.text[:200]}")
    r = client.get("/marketplace/crops?category=vegetable", headers=buyer1)
    check("A2 filter by category (1 tomato)", r.status_code == 200 and r.json()["total"] == 1, r.json()["total"])
    r = client.get("/marketplace/crops?q=tomato", headers=buyer1)
    check("A2 search 'tomato' (1)", r.status_code == 200 and r.json()["total"] == 1, r.json()["total"])
    r = client.get("/marketplace/crops?organic=true", headers=buyer1)
    check("A2 filter organic (1)", r.status_code == 200 and r.json()["total"] == 1, r.json()["total"])
    r = client.get("/marketplace/crops?sort=price_asc", headers=buyer1)
    check(
        "A2 sort by price ascending",
        r.status_code == 200
        and r.json()["items"][0]["price"] <= r.json()["items"][-1]["price"],
        r.text[:200],
    )
    r = client.get("/marketplace/crops?page=1&page_size=1", headers=buyer1)
    check(
        "A2 pagination (page 1 of 2)",
        r.status_code == 200 and r.json()["pages"] == 2 and len(r.json()["items"]) == 1,
        r.json(),
    )
    # Browse filters are permissive by design (vocab is validated on write) — an
    # unknown category yields an empty page, never an error or a crash.
    r = client.get("/marketplace/crops?category=not-a-category", headers=buyer1)
    check(
        "S7 unknown category filter → 200 empty (graceful)",
        r.status_code == 200 and r.json()["total"] == 0,
        f"{r.status_code}: {r.text[:200]}",
    )
    r = client.get("/marketplace/crops?sort=bogus", headers=buyer1)
    check("S7 invalid sort key → 422", r.status_code == 422, f"{r.status_code}")

    # ══════════════════════════════════════════════════════════════════════
    # A4 Seller portal + A5 Product management (+ A6 product marketplace)
    # ══════════════════════════════════════════════════════════════════════
    r = client.post(
        "/marketplace/shop/register",
        json={"shop_name": "Green Agri Supplies", "delivery_available": True, "description": "Organic inputs"},
        headers=seller,
    )
    check("A4 shop register (200)", r.status_code == 200, f"{r.status_code}: {r.text[:200]}")
    shop_user_id = r.json()["user_id"]

    r = client.patch(
        "/marketplace/shop/me",
        json={"delivery_available": False, "opening_hours": "9-6"},
        headers=seller,
    )
    check("A4 shop patch (200)", r.status_code == 200, f"{r.status_code}: {r.text[:200]}")
    check("A4 shop patch persisted", r.json()["opening_hours"] == "9-6", r.json())

    r = client.post(
        "/marketplace/shop/products",
        json={
            "name": "Neem oil spray",
            "category": "pesticide",
            "brand": "BioAgri",
            "price": 250,
            "unit": "l",
            "stock_quantity": 40,
            "organic": True,
        },
        headers=seller,
    )
    check("A5 create product (201)", r.status_code == 201, f"{r.status_code}: {r.text[:200]}")
    product_id = r.json()["id"]

    files = {"files": ("neem.png", _tiny_png(), "image/png")}
    r = client.post("/marketplace/shop/products/images", files=files, headers=seller)
    check("A5 upload product image (200 urls)", r.status_code == 200 and r.json()["urls"], f"{r.text[:200]}")

    r = client.get("/marketplace/shop/products/stats", headers=seller)
    check("A5 product stats (total 1, active 1)", r.status_code == 200 and r.json()["total"] == 1 and r.json()["active"] == 1, r.json())

    r = client.patch(f"/marketplace/shop/products/{product_id}", json={"price": 240}, headers=seller)
    check("A5 patch product (200)", r.status_code == 200 and r.json()["price"] == 240, f"{r.status_code}: {r.text[:200]}")
    r = client.patch(f"/marketplace/shop/products/{product_id}", json={"availability": "out_of_stock"}, headers=seller)
    check("A5 product out-of-stock toggle", r.status_code == 200 and r.json()["availability"] == "out_of_stock", r.text[:200])

    # A6 product marketplace (public browse within auth)
    r = client.get("/marketplace/products", headers=buyer1)
    check("A6 browse products (200, total 1)", r.status_code == 200 and r.json()["total"] == 1, f"{r.status_code}: {r.text[:200]}")
    r = client.get(f"/marketplace/products/{product_id}", headers=buyer1)
    body = r.json()
    check("A6 product detail (200)", r.status_code == 200 and body["id"] == product_id, f"{r.status_code}")
    check(
        "A6 shop summary on product detail",
        body["shop"]["shop_name"] == "Green Agri Supplies" and body["shop"]["rating"] == 0.0,
        body["shop"],
    )

    # S3 Seller ownership — another seller cannot touch this seller's catalog
    seller2 = _register(client, "seller", "Seller Two")
    r = client.get("/marketplace/shop/products", headers=seller2)
    check("S3 second seller catalog is empty", r.status_code == 200 and r.json() == [], r.text[:200])
    r = client.patch(f"/marketplace/shop/products/{product_id}", json={"price": 1}, headers=seller2)
    check("S3 second seller cannot patch product → 404", r.status_code == 404, f"{r.status_code}")
    r = client.delete(f"/marketplace/shop/products/{product_id}", headers=seller2)
    check("S3 second seller cannot delete product → 404", r.status_code == 404, f"{r.status_code}")
    # Wrong-role callers are cut by RBAC (403) before any ownership check…
    r = client.patch(f"/marketplace/crops/{listing_id}", json={"price": 1}, headers=seller)
    check("S3 seller (wrong role) blocked from farmer listing → 403", r.status_code == 403, f"{r.status_code}")
    r = client.delete(f"/marketplace/crops/{listing_id}", headers=buyer1)
    check("S3 buyer (wrong role) blocked from farmer listing → 403", r.status_code == 403, f"{r.status_code}")
    # …while a same-role farmer who isn't the owner gets the 404 enumeration guard.
    r = client.patch(f"/marketplace/crops/{listing_id}", json={"price": 1}, headers=farmer2)
    check("S3 second farmer cannot patch farmer's listing → 404", r.status_code == 404, f"{r.status_code}")
    r = client.delete(f"/marketplace/crops/{listing_id}", headers=farmer2)
    check("S3 second farmer cannot delete farmer's listing → 404", r.status_code == 404, f"{r.status_code}")
    r = client.get("/marketplace/crops/mine", headers=farmer2)
    check("S2 second farmer's listing dashboard is empty", r.status_code == 200 and r.json() == [], r.text[:200])

    # S6 IDOR attempts — bogus ids never leak
    r = client.get("/marketplace/crops/999999", headers=buyer1)
    check("S6 missing listing → 404", r.status_code == 404, f"{r.status_code}")
    r = client.get("/marketplace/products/999999", headers=buyer1)
    check("S6 missing product → 404", r.status_code == 404, f"{r.status_code}")

    # ══════════════════════════════════════════════════════════════════════
    # A9 Favourites (+ S2, S5 ownership)
    # ══════════════════════════════════════════════════════════════════════
    r = client.post("/marketplace/favorites", json={"listing_id": listing_id}, headers=buyer1)
    check("A9 save listing (201)", r.status_code == 201, f"{r.status_code}: {r.text[:200]}")
    favorite_id = r.json()["id"]
    r = client.post("/marketplace/favorites", json={"listing_id": listing_id}, headers=buyer1)
    check("A9 duplicate save is idempotent (same row)", r.status_code == 201 and r.json()["id"] == favorite_id, f"{r.status_code}")
    r = client.post("/marketplace/favorites", json={"product_id": product_id}, headers=buyer1)
    check("A9 save product (201)", r.status_code == 201, f"{r.status_code}: {r.text[:200]}")

    r = client.get("/marketplace/favorites/status?listing_id=" + str(listing_id), headers=buyer1)
    check(
        "A9 favourite status (saved, id attached)",
        r.status_code == 200 and r.json()["favorited"] is True and r.json()["favorite_id"] == favorite_id,
        r.json(),
    )
    r = client.get("/marketplace/favorites/status?listing_id=" + str(listing_id), headers=buyer2)
    check("A9 status scoped per user (not saved for buyer2)", r.status_code == 200 and r.json()["favorited"] is False, r.json())

    r = client.get("/marketplace/favorites", headers=buyer1)
    check("A9 favourites list = 2 (listing + product)", r.status_code == 200 and len(r.json()) == 2, f"{r.status_code}: {r.text[:200]}")
    r = client.get("/marketplace/favorites", headers=outsider)
    check("S2 outsider favourites list is empty", r.status_code == 200 and r.json() == [], r.text[:200])

    r = client.delete(f"/marketplace/favorites/{favorite_id}", headers=buyer2)
    check("S5 other user cannot delete favourite → 404", r.status_code == 404, f"{r.status_code}")
    r = client.delete(f"/marketplace/favorites/{favorite_id}", headers=buyer1)
    check("A9 remove favourite (204)", r.status_code == 204, f"{r.status_code}")
    r = client.get("/marketplace/favorites/status?listing_id=" + str(listing_id), headers=buyer1)
    check("A9 status after remove (not saved)", r.status_code == 200 and r.json()["favorited"] is False, r.json())
    r = client.get("/marketplace/favorites/999999", headers=buyer1)
    check("S6 missing favourite → 405/404 (no such route)", r.status_code in (404, 405), f"{r.status_code}")

    # S7 Invalid input for favourites
    r = client.post("/marketplace/favorites", json={}, headers=buyer1)
    check("S7 favourite with no target → 400", r.status_code == 400, f"{r.status_code}")
    r = client.post("/marketplace/favorites", json={"listing_id": 1, "product_id": product_id}, headers=buyer1)
    check("S7 favourite with both targets → 400", r.status_code == 400, f"{r.status_code}")
    r = client.post("/marketplace/favorites", json={"listing_id": 999999}, headers=buyer1)
    check("S7 favourite unknown target → 400", r.status_code == 400, f"{r.status_code}")

    # ══════════════════════════════════════════════════════════════════════
    # A10 Reviews & ratings + A11 Seller reputation (+ S4, S7)
    # ══════════════════════════════════════════════════════════════════════
    r = client.post(
        "/marketplace/reviews",
        json={"listing_id": listing_id, "rating": 5, "title": "Very fresh", "content": "Crisp and sweet."},
        headers=buyer1,
    )
    check("A10 create review on listing (201)", r.status_code == 201, f"{r.status_code}: {r.text[:200]}")
    review_id = r.json()["id"]
    check(
        "A10 review derives the seller (the farmer)",
        r.json()["seller_id"] == farmer_id,
        r.json(),
    )

    r = client.post(
        "/marketplace/reviews",
        json={"listing_id": listing_id, "rating": 4, "title": "Good", "content": "Nice quality at the price."},
        headers=buyer2,
    )
    check("A10 second buyer review (201)", r.status_code == 201, f"{r.status_code}: {r.text[:200]}")

    r = client.post(
        "/marketplace/reviews",
        json={"listing_id": listing_id, "rating": 3, "content": "Duplicate attempt."},
        headers=buyer1,
    )
    check("A10 duplicate review → 409", r.status_code == 409, f"{r.status_code}")

    # Read model — list with summary + my_review
    r = client.get(f"/marketplace/reviews?listing_id={listing_id}", headers=buyer1)
    body = r.json()
    check("A10 review list = 2", body["total"] == 2 and len(body["items"]) == 2, body)
    check(
        "A10 rating summary (avg 4.5, dist {5:1, 4:1})",
        body["summary"]["average"] == 4.5 and body["summary"]["total"] == 2
        and body["summary"]["distribution"]["5"] == 1 and body["summary"]["distribution"]["4"] == 1,
        body["summary"],
    )
    check("A10 my_review populated for caller", body["my_review"] is not None and body["my_review"]["id"] == review_id, body.get("my_review"))
    r = client.get(f"/marketplace/reviews?listing_id={listing_id}", headers=outsider)
    check("A10 my_review null for a non-reviewer", r.json()["my_review"] is None, r.json().get("my_review"))

    # Seller reputation — reviews aggregate across the farmer's listings
    r = client.get(f"/marketplace/crops/{listing_id}", headers=buyer1)
    body = r.json()
    check(
        "A11 farmer reputation on listing detail (rating 4.5, count 2)",
        body["farmer"]["rating"] == 4.5 and body["farmer"]["review_count"] == 2,
        body["farmer"],
    )
    r = client.get(f"/marketplace/reviews?seller_id={farmer_id}", headers=buyer1)
    check(
        "A11 reviews-by-seller aggregates across listings",
        r.status_code == 200 and r.json()["summary"]["total"] == 2,
        f"{r.status_code}: {r.text[:200]}",
    )
    r = client.get("/marketplace/reviews/mine", headers=buyer1)
    check("A10 my-reviews (buyer1 has 1)", r.status_code == 200 and len(r.json()) == 1, f"{r.status_code}: {r.text[:200]}")

    # S4 Review ownership + S7 invalid review input
    r = client.patch(f"/marketplace/reviews/{review_id}", json={"content": "Even better after washing."}, headers=buyer2)
    check("S4 other user cannot edit review → 404", r.status_code == 404, f"{r.status_code}")
    r = client.delete(f"/marketplace/reviews/{review_id}", headers=buyer2)
    check("S4 other user cannot delete review → 404", r.status_code == 404, f"{r.status_code}")
    r = client.post("/marketplace/reviews", json={"rating": 6, "content": "Bad rating."}, headers=buyer1)
    check("S7 review rating 6 → 422", r.status_code == 422, f"{r.status_code}")
    r = client.post("/marketplace/reviews", json={"rating": 4, "content": "   "}, headers=buyer1)
    check("S7 whitespace-only review → 422", r.status_code == 422, f"{r.status_code}")
    r = client.post("/marketplace/reviews", json={"rating": 4, "content": "No target."}, headers=buyer1)
    check("S7 review with no target → 400", r.status_code == 400, f"{r.status_code}")
    r = client.patch(f"/marketplace/reviews/{review_id}", json={}, headers=buyer1)
    check("S7 empty review update → 422", r.status_code == 422, f"{r.status_code}")
    r = client.post("/marketplace/reviews", json={"listing_id": listing_id, "rating": 5, "content": "Self review."}, headers=farmer)
    check("S7 self-review (farmer rates own listing) → 400", r.status_code == 400, f"{r.status_code}")

    # Edit own review → reputation updates
    r = client.patch(f"/marketplace/reviews/{review_id}", json={"rating": 3, "title": "Pretty good"}, headers=buyer1)
    check("A10 edit own review (200)", r.status_code == 200 and r.json()["rating"] == 3, f"{r.status_code}: {r.text[:200]}")
    r = client.get(f"/marketplace/crops/{listing_id}", headers=buyer1)
    check(
        "A11 reputation follows the edit (avg 3.5)",
        r.json()["farmer"]["rating"] == 3.5,
        r.json()["farmer"],
    )

    # Review a product → the seller's shop reputation
    r = client.post(
        "/marketplace/reviews",
        json={"product_id": product_id, "rating": 5, "content": "Great neem oil."},
        headers=buyer1,
    )
    check("A10 review product (201)", r.status_code == 201, f"{r.status_code}: {r.text[:200]}")
    r = client.get(f"/marketplace/products/{product_id}", headers=buyer1)
    check(
        "A11 shop reputation on product detail (rating 5)",
        r.json()["shop"]["rating"] == 5.0,
        r.json()["shop"],
    )

    # ══════════════════════════════════════════════════════════════════════
    # A7 Buyer↔seller conversations + A8 Messaging (+ S6)
    # ══════════════════════════════════════════════════════════════════════
    r = client.post(
        "/marketplace/conversations",
        json={"listing_id": listing_id, "message": "Is the tomato still available?"},
        headers=buyer1,
    )
    check("A7 create conversation on listing (201)", r.status_code == 201, f"{r.status_code}: {r.text[:300]}")
    conversation_id = r.json()["id"]
    check(
        "A7 conversation seller is the farmer",
        r.json()["seller"]["id"] == farmer_id,
        r.json().get("seller"),
    )
    r = client.post(
        "/marketplace/conversations",
        json={"listing_id": listing_id, "message": "And do you deliver?"},
        headers=buyer1,
    )
    check("A7 duplicate contact reuses thread", r.status_code == 201 and r.json()["id"] == conversation_id, f"{r.status_code}: {r.text[:200]}")

    r = client.get("/marketplace/conversations", headers=farmer)
    inbox = r.json()
    check("A8 farmer inbox has 1 thread", r.status_code == 200 and len(inbox) == 1, f"{r.status_code}: {r.text[:200]}")
    check("A8 inbox unread = 2", inbox[0]["unread_count"] == 2, inbox)
    r = client.post(
        f"/marketplace/conversations/{conversation_id}/messages",
        json={"content": "Yes — 50 kg left, delivering across Nashik."},
        headers=farmer,
    )
    check("A8 seller reply (201)", r.status_code == 201, f"{r.status_code}: {r.text[:200]}")
    r = client.post(f"/marketplace/conversations/{conversation_id}/read", headers=buyer1)
    check("A8 buyer mark-read (200)", r.status_code == 200, f"{r.status_code}: {r.text[:200]}")

    r = client.get(f"/marketplace/conversations/{conversation_id}", headers=outsider)
    check("S6 outsider cannot read thread → 404", r.status_code == 404, f"{r.status_code}")
    r = client.post(f"/marketplace/conversations/{conversation_id}/messages", json={"content": "sneak"}, headers=outsider)
    check("S6 outsider cannot message thread → 404", r.status_code == 404, f"{r.status_code}")

    r = client.post(
        "/marketplace/conversations",
        json={"product_id": product_id, "message": "Is the neem oil in stock?"},
        headers=buyer2,
    )
    check("A7 buyer2 conversation on product (201)", r.status_code == 201, f"{r.status_code}: {r.text[:300]}")
    conv2_id = r.json()["id"]
    # Threads are participant-scoped: the shop seller sees only their product
    # thread (1), never the farmer's listing thread, and vice versa.
    r = client.get("/marketplace/conversations", headers=seller)
    seller_inbox = r.json()
    check(
        "A8 seller inbox has exactly the product thread (1)",
        r.status_code == 200
        and len(seller_inbox) == 1
        and seller_inbox[0]["id"] == conv2_id
        and seller_inbox[0]["last_message_preview"].startswith("Is the neem oil in stock?"),
        f"{r.status_code}: {r.text[:300]}",
    )
    r = client.get("/marketplace/conversations", headers=farmer)
    check(
        "A8 farmer inbox stays isolated (1, own thread only)",
        r.status_code == 200
        and len(r.json()) == 1
        and r.json()[0]["id"] == conversation_id,
        f"{r.status_code}: {r.text[:300]}",
    )
    r = client.post(f"/marketplace/conversations/{conv2_id}/close", headers=seller)
    check("A8 close thread (200)", r.status_code == 200 and r.json()["status"] == "closed", f"{r.status_code}: {r.text[:200]}")
    r = client.post(f"/marketplace/conversations/{conv2_id}/messages", json={"content": "still there?"}, headers=buyer2)
    check("A8 message on closed thread → 409", r.status_code == 409, f"{r.status_code}")

    # S7 Invalid conversation input
    r = client.post("/marketplace/conversations", json={"message": "no context"}, headers=buyer1)
    check("S7 conversation without context → 400", r.status_code == 400, f"{r.status_code}")

    # ── Summary ────────────────────────────────────────────────────────────
    print(f"\n{len(passed)} passed, {len(failed)} failed")
    if failed:
        print("Failed checks:")
        for f in failed:
            print(f"  - {f}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
