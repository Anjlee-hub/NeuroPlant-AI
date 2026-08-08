"""M4 Task 4 — seller portal end-to-end API smoke journey.

Walks the complete seller journey against a live backend:
register seller -> shop profile (register -> read -> edit) -> product lifecycle
(create ×3 -> list -> stats -> mark out of stock -> mark in stock -> archive ->
delete) -> public product market (browse -> search -> filter category/organic/
price/brand -> sort -> detail with shop attached -> archived hidden from feed)
-> RBAC guards (farmer can't hit seller endpoints; product isolation).

Run with the live backend reachable at BASE (start: uvicorn app.main:app --port 8001).
    ./.venv/Scripts/python.exe scripts/m4_task4_smoke.py
"""

import sys
import uuid

import httpx

BASE = "http://127.0.0.1:8001"
API = f"{BASE}/api/v1"

# Windows consoles default to cp1252, which cannot print the en-dashes in the
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


def main() -> None:
    client = httpx.Client(base_url=API, timeout=30)

    # ── Pre-flight ─────────────────────────────────────────────────────────
    r = client.get(f"{BASE}/ready")
    check("GET /ready", r.status_code == 200, r.text)
    r = client.get(f"{BASE}/health")
    check("GET /health", r.status_code == 200, r.text)

    # ── Register + login (seller) ──────────────────────────────────────────
    phone = f"9{str(uuid.uuid4().int)[:9]}"
    payload = {"phone": phone, "name": "Seller Smoke", "role": "seller", "password": "secret123"}
    r = client.post("/auth/register", json=payload)
    check("POST /auth/register (201)", r.status_code == 201, f"{r.status_code}: {r.text[:200]}")
    tokens = r.json()
    seller_headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    # A farmer who must NOT reach seller-only endpoints.
    farmer_phone = f"9{str(uuid.uuid4().int)[:9]}"
    r = client.post(
        "/auth/register",
        json={"phone": farmer_phone, "name": "Farmer Smoke", "role": "farmer", "password": "secret123"},
    )
    check("farmer register (201)", r.status_code == 201, r.text[:200])
    farmer_tokens = r.json()
    farmer_headers = {"Authorization": f"Bearer {farmer_tokens['access_token']}"}

    # ── Shop profile ───────────────────────────────────────────────────────
    shop = {
        "shop_name": "Green Agri Supplies",
        "address": "Main Bazaar, Ludhiana",
        "phone": "+91 98765 43210",
        "delivery_available": False,
        "description": "Farm inputs since 2010.",
        "opening_hours": "Mon–Sat 9:00–19:00",
    }
    r = client.post("/marketplace/shop/register", json=shop, headers=seller_headers)
    check("POST /shop/register (200)", r.status_code == 200, f"{r.status_code}: {r.text[:200]}")
    body = r.json()
    check("shop registered with owner_name", body.get("owner_name") == "Seller Smoke", body)
    check("shop delivery defaults off", body.get("delivery_available") is False, body)
    check("shop rating starts 0", body.get("rating") == 0, body)

    r = client.get("/marketplace/shop/me", headers=seller_headers)
    check("GET /shop/me (200)", r.status_code == 200 and r.json()["shop_name"] == "Green Agri Supplies", r.text[:200])

    # Edit the profile — turn delivery on, update phone.
    r = client.patch("/marketplace/shop/me", json={"delivery_available": True, "phone": "+91 11111 22222"}, headers=seller_headers)
    check("PATCH /shop/me (200)", r.status_code == 200 and r.json()["delivery_available"] is True, r.text[:200])

    # RBAC: a farmer must not register/read the shop.
    r = client.get("/marketplace/shop/me", headers=farmer_headers)
    check("farmer blocked from /shop/me (403)", r.status_code == 403, f"{r.status_code}: {r.text[:200]}")

    # ── Product lifecycle ──────────────────────────────────────────────────
    neem = {
        "name": "Neem oil spray",
        "category": "pesticide",
        "brand": "BioAgri",
        "description": "Cold-pressed neem oil for pest control.",
        "price": 250,
        "unit": "l",
        "stock_quantity": 40,
        "organic": True,
        "manufacturer": "BioAgri Labs",
        "usage_instructions": "Mix 2 ml per litre of water.",
    }
    urea = {
        "name": "Urea 46%",
        "category": "fertilizer",
        "brand": "CropCare",
        "price": 320,
        "unit": "bag",
        "stock_quantity": 15,
        "organic": False,
    }
    jute = {
        "name": "Jute grow bags",
        "category": "tool",
        "brand": "AgroTools",
        "price": 120,
        "unit": "piece",
        "stock_quantity": 100,
        "organic": False,
    }

    r = client.post("/marketplace/shop/products", json=neem, headers=seller_headers)
    check("create neem (201)", r.status_code == 201, f"{r.status_code}: {r.text[:200]}")
    neem_id = r.json()["id"]
    check("neem defaults in_stock", r.json()["availability"] == "in_stock", r.text[:200])

    r = client.post("/marketplace/shop/products", json=urea, headers=seller_headers)
    check("create urea (201)", r.status_code == 201, r.text[:200])
    urea_id = r.json()["id"]

    r = client.post("/marketplace/shop/products", json=jute, headers=seller_headers)
    check("create jute (201)", r.status_code == 201, r.text[:200])
    jute_id = r.json()["id"]

    r = client.get("/marketplace/shop/products", headers=seller_headers)
    check("list own products (3)", r.status_code == 200 and len(r.json()) == 3, f"{r.status_code}: {r.text[:300]}")

    r = client.get("/marketplace/shop/products/stats", headers=seller_headers)
    stats = r.json()
    check("stats total 3 / active 3", stats["total"] == 3 and stats["active"] == 3, stats)
    check("stats zeroed out/archived", stats["out_of_stock"] == 0 and stats["archived"] == 0, stats)

    # Availability: mark urea out of stock, then back in stock.
    r = client.patch(f"/marketplace/shop/products/{urea_id}", json={"availability": "out_of_stock"}, headers=seller_headers)
    check("mark urea out_of_stock", r.status_code == 200 and r.json()["availability"] == "out_of_stock", r.text[:200])
    r = client.patch(f"/marketplace/shop/products/{urea_id}", json={"availability": "in_stock"}, headers=seller_headers)
    check("mark urea back in_stock", r.status_code == 200 and r.json()["availability"] == "in_stock", r.text[:200])

    # Edit a product's price + brand.
    r = client.patch(f"/marketplace/shop/products/{jute_id}", json={"price": 130, "brand": "AgroTools Pro"}, headers=seller_headers)
    check("edit jute price/brand", r.status_code == 200 and r.json()["price"] == 130 and r.json()["brand"] == "AgroTools Pro", r.text[:200])

    # Stats reflect the toggle round-trip.
    r = client.get("/marketplace/shop/products/stats", headers=seller_headers)
    stats = r.json()
    check("stats after round-trip (3/3/0/0)", stats["total"] == 3 and stats["active"] == 3 and stats["out_of_stock"] == 0 and stats["archived"] == 0, stats)

    # ── Public product market ──────────────────────────────────────────────
    r = client.get("/marketplace/products", headers=farmer_headers)
    body = r.json()
    check("browse all products (3)", r.status_code == 200 and body["total"] == 3, f"{r.status_code}: {r.text[:300]}")

    r = client.get("/marketplace/products", params={"q": "neem"}, headers=farmer_headers)
    check("search 'neem' -> 1", r.json()["total"] == 1 and r.json()["items"][0]["name"] == "Neem oil spray", r.text[:300])

    r = client.get("/marketplace/products", params={"category": "fertilizer"}, headers=farmer_headers)
    check("filter fertilizer -> 1", r.json()["total"] == 1 and r.json()["items"][0]["category"] == "fertilizer", r.text[:300])

    r = client.get("/marketplace/products", params={"organic": True}, headers=farmer_headers)
    check("filter organic -> 1 (neem)", r.json()["total"] == 1 and r.json()["items"][0]["organic"] is True, r.text[:300])

    r = client.get("/marketplace/products", params={"min_price": 200, "max_price": 300}, headers=farmer_headers)
    check("price window 200-300 -> 1", r.json()["total"] == 1, r.text[:300])

    r = client.get("/marketplace/products", params={"brand": "agrotools"}, headers=farmer_headers)
    check("brand substring 'agrotools' -> 1", r.json()["total"] == 1, r.text[:300])

    r = client.get("/marketplace/products", params={"sort": "price_asc"}, headers=farmer_headers)
    prices = [p["price"] for p in r.json()["items"]]
    check("sort price_asc", prices == sorted(prices), prices)

    r = client.get("/marketplace/products", params={"page": 1, "page_size": 2}, headers=farmer_headers)
    body = r.json()
    check("pagination page_size=2 -> 2 items, 2 pages", len(body["items"]) == 2 and body["pages"] == 2, body)

    # Detail with the shop attached.
    r = client.get(f"/marketplace/products/{neem_id}", headers=farmer_headers)
    detail = r.json()
    check("detail neem + shop attached", r.status_code == 200 and detail["shop"]["shop_name"] == "Green Agri Supplies" and detail["brand"] == "BioAgri", r.text[:300])

    # ── Archive hides from the public feed ─────────────────────────────────
    r = client.patch(f"/marketplace/shop/products/{jute_id}", json={"availability": "archived"}, headers=seller_headers)
    check("archive jute", r.status_code == 200 and r.json()["availability"] == "archived", r.text[:200])
    r = client.get("/marketplace/shop/products/stats", headers=seller_headers)
    stats = r.json()
    check("stats archived 1 / active 2", stats["archived"] == 1 and stats["active"] == 2, stats)

    r = client.get("/marketplace/products", headers=farmer_headers)
    check("archived hidden from browse (2)", r.json()["total"] == 2, r.text[:300])
    r = client.get(f"/marketplace/products/{jute_id}", headers=farmer_headers)
    check("archived detail still readable (200)", r.status_code == 200, f"{r.status_code}: {r.text[:200]}")
    r = client.get("/marketplace/products", params={"availability": "archived"}, headers=farmer_headers)
    check("archived visible when explicitly requested", r.json()["total"] == 1, r.text[:300])

    # ── Delete + ownership guards ──────────────────────────────────────────
    r = client.delete(f"/marketplace/shop/products/{urea_id}", headers=seller_headers)
    check("delete urea (204)", r.status_code == 204, f"{r.status_code}: {r.text[:200]}")
    r = client.get("/marketplace/shop/products", headers=seller_headers)
    check("list after delete (2)", len(r.json()) == 2, r.text[:300])

    # Enumeration guard: the farmer can't delete a seller's product, even guessing the id.
    r = client.delete(f"/marketplace/shop/products/{neem_id}", headers=farmer_headers)
    check("farmer blocked from delete (403)", r.status_code == 403, f"{r.status_code}: {r.text[:200]}")
    r = client.delete(f"/marketplace/shop/products/{neem_id}", headers=seller_headers)
    check("seller deletes neem (204)", r.status_code == 204, f"{r.status_code}: {r.text[:200]}")

    # A missing product returns 404 for everyone.
    r = client.get("/marketplace/products/999999", headers=farmer_headers)
    check("missing detail -> 404", r.status_code == 404, f"{r.status_code}: {r.text[:200]}")

    # Clean up the archived product so the journey leaves no trace behind.
    r = client.delete(f"/marketplace/shop/products/{jute_id}", headers=seller_headers)
    check("delete archived jute (204)", r.status_code == 204, f"{r.status_code}: {r.text[:200]}")

    # ── Summary ────────────────────────────────────────────────────────────
    print(f"\n{len(passed)} passed, {len(failed)} failed")
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
