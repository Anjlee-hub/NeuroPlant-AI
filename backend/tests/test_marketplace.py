"""M4, Task 1 tests — farmer marketplace backend foundation.

Covers the three role surfaces: farmers create/update/delete/list their own
crop listings, any authenticated user browses/searches/filters and opens
listing details, and sellers register their shop and manage their product
catalog. RBAC (``require_roles`` 403s), ownership guards (404 for other users'
rows — same enumeration guard as scans/recovery/calendar), boundary validation
(vocabularies, prices, quantities) and pagination are all asserted here.
"""

import uuid

from app.db.session import async_session_factory
from app.models.user import User
from app.services.marketplace import MAX_PAGE_SIZE, MarketplaceService
from sqlalchemy import select


def _uuid(n: int) -> str:
    return str(uuid.UUID(int=n))


async def _register(client, phone: str, role: str = "farmer") -> dict:
    resp = await client.post(
        "/api/v1/auth/register",
        json={"phone": phone, "name": "Tester", "role": role, "password": "secret123"},
    )
    assert resp.status_code == 201, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


async def _user_id(db, phone: str) -> int:
    user = await db.scalar(select(User).where(User.phone == phone))
    assert user is not None
    return user.id


def _listing(**overrides) -> dict:
    """A valid create-listing payload; keyword args override fields."""
    payload = {
        "crop_name": "Organic Tomato",
        "category": "vegetable",
        "variety": "Desi",
        "quantity": 50,
        "unit": "kg",
        "price": 30,
        "description": "Fresh farm tomatoes",
        "images": ["/media/tomato.jpg"],
        "organic": True,
        "location": "Punjab",
        "availability": "available",
    }
    payload.update(overrides)
    return payload


def _product(**overrides) -> dict:
    payload = {
        "name": "Neem Oil",
        "category": "fertilizer",
        "brand": "BioAgri",
        "description": "Organic neem oil spray",
        "price": 250,
        "unit": "l",
        "stock_quantity": 40,
        "images": ["/media/neem.jpg"],
    }
    payload.update(overrides)
    return payload


async def _make_listing(client, headers: dict, **overrides) -> dict:
    resp = await client.post(
        "/api/v1/marketplace/crops", json=_listing(**overrides), headers=headers
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


# ── Farmer: listing lifecycle + ownership ──────────────────────────────────


async def test_customer_cannot_create_listing(client):
    headers = await _register(client, "919000000001", role="customer")
    resp = await client.post("/api/v1/marketplace/crops", json=_listing(), headers=headers)
    assert resp.status_code == 403


async def test_unauthenticated_cannot_browse(client):
    resp = await client.get("/api/v1/marketplace/crops")
    assert resp.status_code == 401


async def test_farmer_create_listing_roundtrip(client):
    headers = await _register(client, "919000000002")
    created = await _make_listing(client, headers)
    assert created["crop_name"] == "Organic Tomato"
    assert created["category"] == "vegetable"
    assert created["quantity"] == 50
    assert created["price"] == 30
    assert created["organic"] is True
    assert created["availability"] == "available"
    assert created["images"] == ["/media/tomato.jpg"]
    async with async_session_factory() as db:
        assert created["farmer_id"] == await _user_id(db, "919000000002")
    assert created["id"] > 0


async def test_farmer_lists_own_crops_newest_first(client):
    headers = await _register(client, "919000000003")
    first = await _make_listing(client, headers, crop_name="Potato")
    second = await _make_listing(client, headers, crop_name="Wheat")
    resp = await client.get("/api/v1/marketplace/crops/mine", headers=headers)
    assert resp.status_code == 200
    items = resp.json()
    assert [i["crop_name"] for i in items] == ["Wheat", "Potato"]  # newest first
    assert {i["id"] for i in items} == {first["id"], second["id"]}


async def test_farmer_update_listing_partial(client):
    headers = await _register(client, "919000000004")
    created = await _make_listing(client, headers)
    resp = await client.patch(
        f"/api/v1/marketplace/crops/{created['id']}",
        json={"price": 45, "availability": "limited"},
        headers=headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["price"] == 45
    assert body["availability"] == "limited"
    assert body["crop_name"] == "Organic Tomato"  # untouched field preserved
    assert body["organic"] is True


async def test_farmer_delete_listing(client):
    headers = await _register(client, "919000000005")
    created = await _make_listing(client, headers)
    resp = await client.delete(f"/api/v1/marketplace/crops/{created['id']}", headers=headers)
    assert resp.status_code == 204
    detail = await client.get(f"/api/v1/marketplace/crops/{created['id']}", headers=headers)
    assert detail.status_code == 404
    mine = await client.get("/api/v1/marketplace/crops/mine", headers=headers)
    assert mine.json() == []


async def test_other_farmer_cannot_edit_or_delete_listing(client):
    owner = await _register(client, "919000000006")
    other = await _register(client, "919000000007")
    created = await _make_listing(client, owner)
    patch = await client.patch(
        f"/api/v1/marketplace/crops/{created['id']}", json={"price": 1}, headers=other
    )
    assert patch.status_code == 404  # enumeration guard: not the owner
    delete = await client.delete(f"/api/v1/marketplace/crops/{created['id']}", headers=other)
    assert delete.status_code == 404
    # Owner's listing is untouched.
    mine = await client.get("/api/v1/marketplace/crops/mine", headers=owner)
    assert len(mine.json()) == 1


async def test_listing_detail_404(client):
    headers = await _register(client, "919000000008")
    resp = await client.get("/api/v1/marketplace/crops/999999", headers=headers)
    assert resp.status_code == 404


# ── Customer: browse / search / filter / detail ────────────────────────────


async def _seed_three(client, headers) -> None:
    """Three listings (farmer-owned) used by the browse/filter/sort/search tests."""
    await _make_listing(
        client,
        headers,
        crop_name="Desi Tomato",
        category="vegetable",
        organic=True,
        availability="available",
        price=10,
        location="Punjab",
        description="Fresh desi tomatoes",
    )
    await _make_listing(
        client,
        headers,
        crop_name="Mango",
        category="fruit",
        organic=False,
        availability="sold_out",
        price=50,
        location="Kerala",
        description="Sweet hybrid mango",
    )
    await _make_listing(
        client,
        headers,
        crop_name="Basmati Rice",
        category="grain",
        organic=True,
        availability="limited",
        price=30,
        location="Punjab",
        description="Aged basmati",
    )


async def test_customer_can_browse_paginated(client):
    farmer = await _register(client, "919000000010", role="farmer")
    await _seed_three(client, farmer)
    customer = await _register(client, "919000000011", role="customer")
    resp = await client.get("/api/v1/marketplace/crops", headers=customer)
    body = resp.json()
    assert resp.status_code == 200
    assert body["total"] == 3
    assert body["page"] == 1
    assert body["pages"] == 1
    assert len(body["items"]) == 3

    resp2 = await client.get("/api/v1/marketplace/crops?page_size=2&page=2", headers=customer)
    body2 = resp2.json()
    assert body2["total"] == 3
    assert body2["pages"] == 2
    assert len(body2["items"]) == 1  # second page has the tail


async def test_browse_filters(client):
    farmer = await _register(client, "919000000012", role="farmer")
    await _seed_three(client, farmer)
    customer = await _register(client, "919000000013", role="customer")

    async def names(params: str) -> list[str]:
        resp = await client.get(f"/api/v1/marketplace/crops{params}", headers=customer)
        assert resp.status_code == 200, resp.text
        return sorted(i["crop_name"] for i in resp.json()["items"])

    assert await names("?category=fruit") == ["Mango"]
    assert await names("?organic=true") == ["Basmati Rice", "Desi Tomato"]
    assert await names("?availability=sold_out") == ["Mango"]
    assert await names("?min_price=20") == ["Basmati Rice", "Mango"]
    assert await names("?max_price=10") == ["Desi Tomato"]
    assert await names("?min_price=20&max_price=40") == ["Basmati Rice"]
    assert await names("?location=Punjab") == ["Basmati Rice", "Desi Tomato"]
    assert await names("?category=spice") == []  # no matches, not an error


async def test_browse_sort(client):
    farmer = await _register(client, "919000000014", role="farmer")
    await _seed_three(client, farmer)
    customer = await _register(client, "919000000015", role="customer")

    resp = await client.get("/api/v1/marketplace/crops?sort=price_asc", headers=customer)
    names_asc = [i["crop_name"] for i in resp.json()["items"]]
    assert names_asc == ["Desi Tomato", "Basmati Rice", "Mango"]
    resp = await client.get("/api/v1/marketplace/crops?sort=price_desc", headers=customer)
    names_desc = [i["crop_name"] for i in resp.json()["items"]]
    assert names_desc == ["Mango", "Basmati Rice", "Desi Tomato"]


async def test_search_crops(client):
    farmer = await _register(client, "919000000016", role="farmer")
    await _seed_three(client, farmer)
    customer = await _register(client, "919000000017", role="customer")

    async def search(q: str) -> list[str]:
        resp = await client.get(f"/api/v1/marketplace/crops/search?q={q}", headers=customer)
        assert resp.status_code == 200, resp.text
        return sorted(i["crop_name"] for i in resp.json()["items"])

    assert await search("tomato") == ["Desi Tomato"]  # crop_name
    assert await search("hybrid") == ["Mango"]  # variety
    assert await search("basmati") == ["Basmati Rice"]  # description
    assert await search("Punjab") == ["Basmati Rice", "Desi Tomato"]  # location
    assert await search("zzz-nothing") == []
    # Search composes with filters.
    resp = await client.get(
        "/api/v1/marketplace/crops/search?q=Punjab&organic=false", headers=customer
    )
    assert resp.json()["items"] == []


async def test_search_requires_q(client):
    headers = await _register(client, "919000000018", role="customer")
    resp = await client.get("/api/v1/marketplace/crops/search", headers=headers)
    assert resp.status_code == 422


async def test_listing_detail_includes_farmer(client):
    headers = await _register(client, "919000000015")
    created = await _make_listing(client, headers)
    resp = await client.get(f"/api/v1/marketplace/crops/{created['id']}", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["farmer"]["name"] == "Tester"
    assert body["farmer"]["id"] == created["farmer_id"]
    assert "verified" in body["farmer"]


# ── Seller: shop registration + product catalog ────────────────────────────


async def test_non_seller_cannot_register_shop(client):
    roles = (("919000000010", "farmer"), ("919000000011", "customer"), ("919000000012", "expert"))
    for phone, role in roles:
        headers = await _register(client, phone, role=role)
        resp = await client.post(
            "/api/v1/marketplace/shop/register",
            json={"shop_name": "Farm Shop", "delivery_available": True},
            headers=headers,
        )
        assert resp.status_code == 403, role


async def test_seller_register_shop(client):
    headers = await _register(client, "919000000020", role="seller")
    resp = await client.post(
        "/api/v1/marketplace/shop/register",
        json={
            "shop_name": "Green Agri Supplies",
            "address": "Main Bazaar, Ludhiana",
            "phone": "+911234567890",
            "delivery_available": True,
        },
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["shop_name"] == "Green Agri Supplies"
    assert body["address"] == "Main Bazaar, Ludhiana"
    assert body["phone"] == "+911234567890"
    assert body["delivery_available"] is True
    assert body["rating"] == 0.0
    assert body["owner_name"] == "Tester"
    assert body["products"] == []


async def test_seller_shop_me_includes_products(client):
    headers = await _register(client, "919000000021", role="seller")
    await client.post(
        "/api/v1/marketplace/shop/register",
        json={"shop_name": "AgroKart", "delivery_available": False},
        headers=headers,
    )
    await client.post("/api/v1/marketplace/shop/products", json=_product(), headers=headers)
    resp = await client.get("/api/v1/marketplace/shop/me", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["shop_name"] == "AgroKart"
    assert len(body["products"]) == 1
    assert body["products"][0]["name"] == "Neem Oil"


async def test_seller_adds_each_product_category(client):
    headers = await _register(client, "919000000022", role="seller")
    await client.post(
        "/api/v1/marketplace/shop/register", json={"shop_name": "AgroKart"}, headers=headers
    )
    for category in ("fertilizer", "pesticide", "seed", "tool"):
        resp = await client.post(
            "/api/v1/marketplace/shop/products",
            json=_product(name=f"Product-{category}", category=category, price=100),
            headers=headers,
        )
        assert resp.status_code == 201, resp.text
        assert resp.json()["category"] == category


async def test_seller_update_product_partial(client):
    headers = await _register(client, "919000000023", role="seller")
    await client.post(
        "/api/v1/marketplace/shop/register", json={"shop_name": "AgroKart"}, headers=headers
    )
    created = await client.post(
        "/api/v1/marketplace/shop/products", json=_product(price=250), headers=headers
    )
    product_id = created.json()["id"]
    resp = await client.patch(
        f"/api/v1/marketplace/shop/products/{product_id}",
        json={"price": 199, "stock_quantity": 5},
        headers=headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["price"] == 199
    assert body["stock_quantity"] == 5
    assert body["name"] == "Neem Oil"  # untouched field preserved


async def test_other_seller_cannot_update_product(client):
    seller_a = await _register(client, "919000000024", role="seller")
    seller_b = await _register(client, "919000000025", role="seller")
    await client.post(
        "/api/v1/marketplace/shop/register", json={"shop_name": "Shop A"}, headers=seller_a
    )
    await client.post(
        "/api/v1/marketplace/shop/register", json={"shop_name": "Shop B"}, headers=seller_b
    )
    created = await client.post(
        "/api/v1/marketplace/shop/products", json=_product(), headers=seller_a
    )
    product_id = created.json()["id"]
    resp = await client.patch(
        f"/api/v1/marketplace/shop/products/{product_id}",
        json={"price": 1},
        headers=seller_b,
    )
    assert resp.status_code == 404  # enumeration guard


async def test_seller_can_add_product_before_filling_shop(client):
    # The seller's profile is auto-created at registration, so a product can be
    # listed even before register_shop fills in the shop_name.
    headers = await _register(client, "919000000026", role="seller")
    resp = await client.post("/api/v1/marketplace/shop/products", json=_product(), headers=headers)
    assert resp.status_code == 201, resp.text
    shop = await client.get("/api/v1/marketplace/shop/me", headers=headers)
    body = shop.json()
    assert body["shop_name"] is None
    assert len(body["products"]) == 1
    assert body["products"][0]["name"] == "Neem Oil"


async def test_admin_can_create_listing(client):
    headers = await _register(client, "919000000027", role="admin")
    created = await _make_listing(client, headers)
    assert created["crop_name"] == "Organic Tomato"


# ── Boundary validation ────────────────────────────────────────────────────


async def test_listing_validation(client):
    headers = await _register(client, "919000000030")
    bad_payloads = [
        _listing(category="mystery"),
        _listing(unit="tonne"),
        _listing(availability="sold"),
        _listing(price=-1),
        _listing(quantity=0),
        _listing(crop_name=""),
    ]
    for payload in bad_payloads:
        resp = await client.post("/api/v1/marketplace/crops", json=payload, headers=headers)
        assert resp.status_code == 422, payload


async def test_product_validation(client):
    headers = await _register(client, "919000000031", role="seller")
    await client.post(
        "/api/v1/marketplace/shop/register", json={"shop_name": "AgroKart"}, headers=headers
    )
    for payload in (
        _product(category="chemical"),
        _product(price=-5),
        _product(unit="pallet"),
        _product(stock_quantity=-1),
    ):
        resp = await client.post("/api/v1/marketplace/shop/products", json=payload, headers=headers)
        assert resp.status_code == 422, payload


# ── Service-level pagination policy ────────────────────────────────────────


async def test_page_size_is_clamped(db):
    service = MarketplaceService(db)
    result = await service.browse_crops(page=1, page_size=999999)
    assert result.page_size == MAX_PAGE_SIZE
    # Invalid sort falls back to newest (never raises).
    result2 = await service.browse_crops(sort="bogus")
    assert result2.items == []
