"""M4, Task 6 tests — marketplace trust: favourites + reviews & ratings.

Covers the saved-items layer (idempotent add, ownership-guarded remove, list,
button-status, listing/product targets, invalid + deleted targets) and the
reviews & ratings layer (create, boundary validation, duplicate + self-review
prevention, update/delete own review, ownership isolation, paginated list with
rating summary + distribution, seller & item reputation, and review-history
survival when the item is deleted).
"""

from app.db.session import async_session_factory
from app.models.user import User
from sqlalchemy import select


def _phone(n: int) -> str:
    return f"9{n:010d}"


async def _register(client, phone: str, role: str = "customer") -> dict:
    resp = await client.post(
        "/api/v1/auth/register",
        json={"phone": phone, "name": "Trust Tester", "role": role, "password": "secret123"},
    )
    assert resp.status_code == 201, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


async def _farmer_with_listing(client, phone: str) -> tuple[dict, int]:
    """Register a farmer and create one crop listing."""
    headers = await _register(client, phone, role="farmer")
    resp = await client.post(
        "/api/v1/marketplace/crops",
        json={
            "crop_name": "Organic Tomato",
            "category": "vegetable",
            "quantity": 50,
            "unit": "kg",
            "price": 30,
            "organic": True,
            "availability": "available",
        },
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    return headers, resp.json()["id"]


async def _farmer_with_listings(client, phone: str, count: int = 2) -> tuple[dict, list[int]]:
    """Register one farmer and create ``count`` listings for them (so seller
    reputation can be tested across several items of a single farmer)."""
    headers = await _register(client, phone, role="farmer")
    listing_ids = []
    for i in range(count):
        resp = await client.post(
            "/api/v1/marketplace/crops",
            json={
                "crop_name": f"Organic Crop {i}",
                "category": "vegetable",
                "quantity": 50,
                "unit": "kg",
                "price": 30 + i,
                "organic": True,
                "availability": "available",
            },
            headers=headers,
        )
        assert resp.status_code == 201, resp.text
        listing_ids.append(resp.json()["id"])
    return headers, listing_ids


async def _seller_with_product(client, phone: str) -> tuple[dict, int]:
    """Register a seller, register their shop and create one product."""
    headers = await _register(client, phone, role="seller")
    resp = await client.post(
        "/api/v1/marketplace/shop/register",
        json={"shop_name": "Green Agri", "delivery_available": True},
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    resp = await client.post(
        "/api/v1/marketplace/shop/products",
        json={
            "name": "Neem Oil",
            "category": "pesticide",
            "brand": "BioAgri",
            "description": "Cold-pressed neem oil",
            "price": 250,
            "unit": "l",
            "stock_quantity": 40,
            "organic": True,
            "images": ["/media/neem.jpg"],
        },
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    return headers, resp.json()["id"]


async def _user_id(db, phone: str) -> int:
    user = await db.scalar(select(User).where(User.phone == phone))
    assert user is not None
    return user.id


# ── Favourites: auth ──────────────────────────────────────────────────────


async def test_favourites_require_auth(client):
    endpoints = [
        ("get", "/api/v1/marketplace/favorites"),
        ("get", "/api/v1/marketplace/favorites/status?listing_id=1"),
        ("post", "/api/v1/marketplace/favorites"),
        ("delete", "/api/v1/marketplace/favorites/1"),
    ]
    for method, url in endpoints:
        resp = await client.request(method, url, json={"listing_id": 1})
        assert resp.status_code == 401, (method, url)


# ── Favourites: add / remove / list ───────────────────────────────────────


async def test_add_favourite_listing(client):
    _, listing_id = await _farmer_with_listing(client, _phone(1))
    buyer = await _register(client, _phone(2))
    resp = await client.post(
        "/api/v1/marketplace/favorites", json={"listing_id": listing_id}, headers=buyer
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["listing"]["id"] == listing_id
    assert body["listing"]["crop_name"] == "Organic Tomato"
    assert body["product"] is None


async def test_add_favourite_product(client):
    _, product_id = await _seller_with_product(client, _phone(3))
    buyer = await _register(client, _phone(4))
    resp = await client.post(
        "/api/v1/marketplace/favorites", json={"product_id": product_id}, headers=buyer
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["product"]["id"] == product_id
    assert body["product"]["name"] == "Neem Oil"
    assert body["listing"] is None


async def test_duplicate_add_is_idempotent(client):
    _, listing_id = await _farmer_with_listing(client, _phone(5))
    buyer = await _register(client, _phone(6))
    first = await client.post(
        "/api/v1/marketplace/favorites", json={"listing_id": listing_id}, headers=buyer
    )
    assert first.status_code == 201
    second = await client.post(
        "/api/v1/marketplace/favorites", json={"listing_id": listing_id}, headers=buyer
    )
    assert second.status_code == 201
    assert second.json()["id"] == first.json()["id"]


async def test_remove_favourite(client):
    _, listing_id = await _farmer_with_listing(client, _phone(7))
    buyer = await _register(client, _phone(8))
    fav = await client.post(
        "/api/v1/marketplace/favorites", json={"listing_id": listing_id}, headers=buyer
    )
    favorite_id = fav.json()["id"]
    resp = await client.delete(f"/api/v1/marketplace/favorites/{favorite_id}", headers=buyer)
    assert resp.status_code == 204
    assert (await client.get("/api/v1/marketplace/favorites", headers=buyer)).json() == []
    # Removing again is a 404 (row is gone).
    again = await client.delete(f"/api/v1/marketplace/favorites/{favorite_id}", headers=buyer)
    assert again.status_code == 404


async def test_favourite_ownership_is_isolated(client):
    _, listing_id = await _farmer_with_listing(client, _phone(9))
    buyer_a = await _register(client, _phone(10))
    buyer_b = await _register(client, _phone(11))
    fav = await client.post(
        "/api/v1/marketplace/favorites", json={"listing_id": listing_id}, headers=buyer_a
    )
    favorite_id = fav.json()["id"]

    # Another user's saved row is unreachable (enumeration guard).
    resp = await client.delete(f"/api/v1/marketplace/favorites/{favorite_id}", headers=buyer_b)
    assert resp.status_code == 404
    # Missing id → 404.
    resp = await client.delete("/api/v1/marketplace/favorites/999999", headers=buyer_a)
    assert resp.status_code == 404
    # Own row unaffected; other user's list stays empty.
    assert len((await client.get("/api/v1/marketplace/favorites", headers=buyer_a)).json()) == 1
    assert (await client.get("/api/v1/marketplace/favorites", headers=buyer_b)).json() == []


async def test_list_favourites_newest_first(client):
    _, listing_id = await _farmer_with_listing(client, _phone(12))
    _, product_id = await _seller_with_product(client, _phone(13))
    buyer = await _register(client, _phone(14))
    await client.post(
        "/api/v1/marketplace/favorites", json={"listing_id": listing_id}, headers=buyer
    )
    await client.post(
        "/api/v1/marketplace/favorites", json={"product_id": product_id}, headers=buyer
    )
    body = (await client.get("/api/v1/marketplace/favorites", headers=buyer)).json()
    assert len(body) == 2
    # Newest first — the product was saved last.
    assert body[0]["product"]["id"] == product_id
    assert body[1]["listing"]["id"] == listing_id


async def test_favourite_status(client):
    _, listing_id = await _farmer_with_listing(client, _phone(15))
    buyer = await _register(client, _phone(16))
    not_saved = await client.get(
        "/api/v1/marketplace/favorites/status",
        params={"listing_id": listing_id},
        headers=buyer,
    )
    assert not_saved.status_code == 200
    assert not_saved.json() == {
        "favorited": False,
        "favorite_id": None,
        "listing_id": listing_id,
        "product_id": None,
    }

    fav = await client.post(
        "/api/v1/marketplace/favorites", json={"listing_id": listing_id}, headers=buyer
    )
    saved = await client.get(
        "/api/v1/marketplace/favorites/status",
        params={"listing_id": listing_id},
        headers=buyer,
    )
    body = saved.json()
    assert body["favorited"] is True
    assert body["favorite_id"] == fav.json()["id"]
    assert body["listing_id"] == listing_id


async def test_favourite_requires_exactly_one_target(client):
    _, listing_id = await _farmer_with_listing(client, _phone(17))
    buyer = await _register(client, _phone(18))
    # Both targets → 400.
    resp = await client.post(
        "/api/v1/marketplace/favorites",
        json={"listing_id": listing_id, "product_id": 1},
        headers=buyer,
    )
    assert resp.status_code == 400
    # Neither target → 400.
    resp = await client.post("/api/v1/marketplace/favorites", json={}, headers=buyer)
    assert resp.status_code == 400
    # Unknown reference → 400 (never a leak).
    resp = await client.post(
        "/api/v1/marketplace/favorites", json={"listing_id": 999999}, headers=buyer
    )
    assert resp.status_code == 400
    # Status with two targets → 400.
    resp = await client.get(
        "/api/v1/marketplace/favorites/status",
        params={"listing_id": listing_id, "product_id": 1},
        headers=buyer,
    )
    assert resp.status_code == 400


async def test_favourite_of_deleted_listing_disappears(client):
    farmer, listing_id = await _farmer_with_listing(client, _phone(19))
    buyer = await _register(client, _phone(20))
    await client.post(
        "/api/v1/marketplace/favorites", json={"listing_id": listing_id}, headers=buyer
    )
    resp = await client.delete(f"/api/v1/marketplace/crops/{listing_id}", headers=farmer)
    assert resp.status_code == 204

    # The dead saved copy is no longer listed.
    assert (await client.get("/api/v1/marketplace/favorites", headers=buyer)).json() == []
    # Status for a deleted item is not meaningful → 400.
    resp = await client.get(
        "/api/v1/marketplace/favorites/status",
        params={"listing_id": listing_id},
        headers=buyer,
    )
    assert resp.status_code == 400


# ── Reviews: auth ─────────────────────────────────────────────────────────


async def test_reviews_require_auth(client):
    endpoints = [
        ("get", "/api/v1/marketplace/reviews?listing_id=1"),
        ("get", "/api/v1/marketplace/reviews/mine"),
        ("post", "/api/v1/marketplace/reviews"),
        ("patch", "/api/v1/marketplace/reviews/1"),
        ("delete", "/api/v1/marketplace/reviews/1"),
    ]
    for method, url in endpoints:
        resp = await client.request(
            method, url, json={"listing_id": 1, "rating": 5, "content": "good"}
        )
        assert resp.status_code == 401, (method, url)


# ── Reviews: create + validation ──────────────────────────────────────────


async def test_create_review_listing(client):
    _, listing_id = await _farmer_with_listing(client, _phone(21))
    buyer = await _register(client, _phone(22))
    resp = await client.post(
        "/api/v1/marketplace/reviews",
        json={
            "listing_id": listing_id,
            "rating": 5,
            "title": "Fresh",
            "content": "Very fresh tomatoes",
        },
        headers=buyer,
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["rating"] == 5
    assert body["title"] == "Fresh"
    assert body["content"] == "Very fresh tomatoes"
    assert body["reviewer_name"] == "Trust Tester"
    assert body["listing"]["id"] == listing_id
    assert body["listing"]["crop_name"] == "Organic Tomato"
    assert body["product"] is None


async def test_create_review_product(client):
    _, product_id = await _seller_with_product(client, _phone(23))
    buyer = await _register(client, _phone(24))
    resp = await client.post(
        "/api/v1/marketplace/reviews",
        json={"product_id": product_id, "rating": 4, "content": "Works well"},
        headers=buyer,
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["product"]["id"] == product_id
    assert body["product"]["name"] == "Neem Oil"
    assert body["listing"] is None


async def test_review_rating_bounds(client):
    _, listing_id = await _farmer_with_listing(client, _phone(25))
    buyer = await _register(client, _phone(26))
    for rating in (0, 6, -1):
        resp = await client.post(
            "/api/v1/marketplace/reviews",
            json={"listing_id": listing_id, "rating": rating, "content": "ok"},
            headers=buyer,
        )
        assert resp.status_code == 422, rating
    # Missing rating → 422.
    resp = await client.post(
        "/api/v1/marketplace/reviews",
        json={"listing_id": listing_id, "content": "ok"},
        headers=buyer,
    )
    assert resp.status_code == 422


async def test_review_title_content_validation(client):
    _, listing_id = await _farmer_with_listing(client, _phone(27))
    buyer = await _register(client, _phone(28))
    cases = [
        {"content": ""},  # empty content
        {"content": "   "},  # whitespace-only content
        {"content": "x" * 2001},  # over the 2000-char limit
        {"content": "ok", "title": "t" * 201},  # title over the 200-char limit
        {},  # missing content
    ]
    for payload in cases:
        resp = await client.post(
            "/api/v1/marketplace/reviews",
            json={"listing_id": listing_id, "rating": 5, **payload},
            headers=buyer,
        )
        assert resp.status_code == 422, payload


async def test_duplicate_review_prevented(client):
    _, listing_id = await _farmer_with_listing(client, _phone(29))
    buyer = await _register(client, _phone(30))
    first = await client.post(
        "/api/v1/marketplace/reviews",
        json={"listing_id": listing_id, "rating": 5, "content": "great"},
        headers=buyer,
    )
    assert first.status_code == 201
    second = await client.post(
        "/api/v1/marketplace/reviews",
        json={"listing_id": listing_id, "rating": 3, "content": "changed my mind"},
        headers=buyer,
    )
    assert second.status_code == 409


async def test_self_review_prevented(client):
    farmer, listing_id = await _farmer_with_listing(client, _phone(31))
    resp = await client.post(
        "/api/v1/marketplace/reviews",
        json={"listing_id": listing_id, "rating": 5, "content": "my own crop"},
        headers=farmer,
    )
    assert resp.status_code == 400
    # A seller cannot review their own product either.
    seller, product_id = await _seller_with_product(client, _phone(32))
    resp = await client.post(
        "/api/v1/marketplace/reviews",
        json={"product_id": product_id, "rating": 5, "content": "my own product"},
        headers=seller,
    )
    assert resp.status_code == 400


async def test_review_requires_exactly_one_target(client):
    _, listing_id = await _farmer_with_listing(client, _phone(33))
    buyer = await _register(client, _phone(34))
    # Both targets → 400.
    resp = await client.post(
        "/api/v1/marketplace/reviews",
        json={"listing_id": listing_id, "product_id": 1, "rating": 5, "content": "ok"},
        headers=buyer,
    )
    assert resp.status_code == 400
    # Neither target → 400.
    resp = await client.post(
        "/api/v1/marketplace/reviews",
        json={"rating": 5, "content": "ok"},
        headers=buyer,
    )
    assert resp.status_code == 400
    # Unknown reference → 400 (never a leak).
    resp = await client.post(
        "/api/v1/marketplace/reviews",
        json={"listing_id": 999999, "rating": 5, "content": "ok"},
        headers=buyer,
    )
    assert resp.status_code == 400


# ── Reviews: update / delete / ownership ──────────────────────────────────


async def test_update_own_review_partial(client):
    _, listing_id = await _farmer_with_listing(client, _phone(35))
    buyer = await _register(client, _phone(36))
    review = await client.post(
        "/api/v1/marketplace/reviews",
        json={"listing_id": listing_id, "rating": 3, "title": "Meh", "content": "Average quality"},
        headers=buyer,
    )
    review_id = review.json()["id"]
    resp = await client.patch(
        f"/api/v1/marketplace/reviews/{review_id}", json={"rating": 5}, headers=buyer
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["rating"] == 5
    assert body["title"] == "Meh"  # untouched fields preserved
    assert body["content"] == "Average quality"
    # An empty update is rejected.
    blank = await client.patch(f"/api/v1/marketplace/reviews/{review_id}", json={}, headers=buyer)
    assert blank.status_code == 422


async def test_delete_own_review(client):
    _, listing_id = await _farmer_with_listing(client, _phone(37))
    buyer = await _register(client, _phone(38))
    review = await client.post(
        "/api/v1/marketplace/reviews",
        json={"listing_id": listing_id, "rating": 4, "content": "nice"},
        headers=buyer,
    )
    review_id = review.json()["id"]
    resp = await client.delete(f"/api/v1/marketplace/reviews/{review_id}", headers=buyer)
    assert resp.status_code == 204
    assert (await client.get("/api/v1/marketplace/reviews/mine", headers=buyer)).json() == []
    # Deleting again → 404.
    again = await client.delete(f"/api/v1/marketplace/reviews/{review_id}", headers=buyer)
    assert again.status_code == 404


async def test_review_ownership_is_isolated(client):
    _, listing_id = await _farmer_with_listing(client, _phone(39))
    buyer_a = await _register(client, _phone(40))
    buyer_b = await _register(client, _phone(41))
    review = await client.post(
        "/api/v1/marketplace/reviews",
        json={"listing_id": listing_id, "rating": 5, "content": "great"},
        headers=buyer_a,
    )
    review_id = review.json()["id"]

    # Another user's review is unreachable (enumeration guard).
    assert (
        await client.patch(
            f"/api/v1/marketplace/reviews/{review_id}", json={"rating": 1}, headers=buyer_b
        )
    ).status_code == 404
    assert (
        await client.delete(f"/api/v1/marketplace/reviews/{review_id}", headers=buyer_b)
    ).status_code == 404
    # Missing id → 404.
    assert (
        await client.patch(
            "/api/v1/marketplace/reviews/999999", json={"rating": 1}, headers=buyer_a
        )
    ).status_code == 404
    # The author can still edit their own.
    assert (
        await client.patch(
            f"/api/v1/marketplace/reviews/{review_id}", json={"rating": 2}, headers=buyer_a
        )
    ).status_code == 200


# ── Reviews: list / summary / reputation ──────────────────────────────────


async def test_list_reviews_with_summary_and_my_review(client):
    _, listing_id = await _farmer_with_listing(client, _phone(42))
    buyer_a = await _register(client, _phone(43))
    buyer_b = await _register(client, _phone(44))
    await client.post(
        "/api/v1/marketplace/reviews",
        json={"listing_id": listing_id, "rating": 5, "content": "A"},
        headers=buyer_a,
    )
    await client.post(
        "/api/v1/marketplace/reviews",
        json={"listing_id": listing_id, "rating": 3, "content": "B"},
        headers=buyer_b,
    )

    resp = await client.get(
        "/api/v1/marketplace/reviews", params={"listing_id": listing_id}, headers=buyer_a
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 2
    assert body["pages"] == 1
    assert [item["rating"] for item in body["items"]] == [3, 5]  # newest first
    assert body["summary"]["average"] == 4.0
    assert body["summary"]["total"] == 2
    # 5→1 distribution, zero-filled for the missing star values. JSON object
    # keys are strings, so the star values arrive as "1".."5".
    assert body["summary"]["distribution"] == {"5": 1, "4": 0, "3": 1, "2": 0, "1": 0}
    # The caller's own review of the item is attached.
    assert body["my_review"]["rating"] == 5


async def test_review_list_requires_exactly_one_scope(client):
    buyer = await _register(client, _phone(45))
    # No scope → 400.
    resp = await client.get("/api/v1/marketplace/reviews", headers=buyer)
    assert resp.status_code == 400
    # Two scopes → 400.
    resp = await client.get(
        "/api/v1/marketplace/reviews",
        params={"listing_id": 1, "product_id": 2},
        headers=buyer,
    )
    assert resp.status_code == 400


async def test_review_pagination(client):
    _, listing_id = await _farmer_with_listing(client, _phone(46))
    reviewers = []
    for i in range(5):
        headers = await _register(client, _phone(47 + i))
        reviewers.append(headers)
        resp = await client.post(
            "/api/v1/marketplace/reviews",
            json={"listing_id": listing_id, "rating": 5, "content": f"r{i}"},
            headers=headers,
        )
        assert resp.status_code == 201

    first = (
        await client.get(
            "/api/v1/marketplace/reviews",
            params={"listing_id": listing_id, "page": 1, "page_size": 2},
            headers=reviewers[0],
        )
    ).json()
    assert first["total"] == 5
    assert first["pages"] == 3
    assert first["page"] == 1
    assert len(first["items"]) == 2

    second = (
        await client.get(
            "/api/v1/marketplace/reviews",
            params={"listing_id": listing_id, "page": 2, "page_size": 2},
            headers=reviewers[0],
        )
    ).json()
    assert second["page"] == 2 and len(second["items"]) == 2

    third = (
        await client.get(
            "/api/v1/marketplace/reviews",
            params={"listing_id": listing_id, "page": 3, "page_size": 2},
            headers=reviewers[0],
        )
    ).json()
    assert third["page"] == 3 and len(third["items"]) == 1

    # Every review is reached exactly once across the pages.
    seen = [item["id"] for item in first["items"] + second["items"] + third["items"]]
    assert len(seen) == len(set(seen)) == 5


async def test_seller_reputation_aggregates_across_items(client):
    _, [listing_a, listing_b] = await _farmer_with_listings(client, _phone(52))
    _, product_id = await _seller_with_product(client, _phone(54))
    buyer = await _register(client, _phone(55))

    await client.post(
        "/api/v1/marketplace/reviews",
        json={"listing_id": listing_a, "rating": 5, "content": "best"},
        headers=buyer,
    )
    await client.post(
        "/api/v1/marketplace/reviews",
        json={"listing_id": listing_b, "rating": 3, "content": "ok"},
        headers=buyer,
    )
    await client.post(
        "/api/v1/marketplace/reviews",
        json={"product_id": product_id, "rating": 4, "content": "fine"},
        headers=buyer,
    )

    async with async_session_factory() as db:
        farmer_id = await _user_id(db, _phone(52))
        seller_id = await _user_id(db, _phone(54))

    # The farmer's reputation spans both of their listings.
    farmer_reviews = (
        await client.get(
            "/api/v1/marketplace/reviews",
            params={"seller_id": farmer_id},
            headers=buyer,
        )
    ).json()
    assert farmer_reviews["total"] == 2
    assert farmer_reviews["summary"]["average"] == 4.0
    assert farmer_reviews["summary"]["distribution"] == {"5": 1, "4": 0, "3": 1, "2": 0, "1": 0}

    # The seller's reputation spans their product.
    seller_reviews = (
        await client.get(
            "/api/v1/marketplace/reviews",
            params={"seller_id": seller_id},
            headers=buyer,
        )
    ).json()
    assert seller_reviews["total"] == 1
    assert seller_reviews["summary"]["average"] == 4.0


async def test_reputation_shown_on_details(client):
    _, [listing_a, listing_b] = await _farmer_with_listings(client, _phone(56))
    seller, product_id = await _seller_with_product(client, _phone(58))
    buyer = await _register(client, _phone(59))

    await client.post(
        "/api/v1/marketplace/reviews",
        json={"listing_id": listing_a, "rating": 5, "content": "great"},
        headers=buyer,
    )
    await client.post(
        "/api/v1/marketplace/reviews",
        json={"listing_id": listing_b, "rating": 3, "content": "ok"},
        headers=buyer,
    )
    await client.post(
        "/api/v1/marketplace/reviews",
        json={"product_id": product_id, "rating": 2, "content": "poor"},
        headers=buyer,
    )

    # Listing detail → the farmer block shows review-driven reputation.
    detail = (await client.get(f"/api/v1/marketplace/crops/{listing_a}", headers=buyer)).json()
    assert detail["farmer"]["rating"] == 4.0
    assert detail["farmer"]["review_count"] == 2

    # Product detail → the shop block shows the review-driven rating.
    pdetail = (await client.get(f"/api/v1/marketplace/products/{product_id}", headers=buyer)).json()
    assert pdetail["shop"]["rating"] == 2.0

    # The seller's own shop surface uses the same source.
    shop = (await client.get("/api/v1/marketplace/shop/me", headers=seller)).json()
    assert shop["rating"] == 2.0


async def test_mine_lists_only_callers_reviews(client):
    _, listing_a = await _farmer_with_listing(client, _phone(60))
    _, listing_b = await _farmer_with_listing(client, _phone(61))
    buyer_a = await _register(client, _phone(62))
    buyer_b = await _register(client, _phone(63))
    await client.post(
        "/api/v1/marketplace/reviews",
        json={"listing_id": listing_a, "rating": 5, "content": "a"},
        headers=buyer_a,
    )
    await client.post(
        "/api/v1/marketplace/reviews",
        json={"listing_id": listing_b, "rating": 4, "content": "b"},
        headers=buyer_b,
    )

    mine_a = (await client.get("/api/v1/marketplace/reviews/mine", headers=buyer_a)).json()
    assert len(mine_a) == 1
    assert mine_a[0]["rating"] == 5
    assert mine_a[0]["listing"]["id"] == listing_a

    mine_b = (await client.get("/api/v1/marketplace/reviews/mine", headers=buyer_b)).json()
    assert len(mine_b) == 1
    assert mine_b[0]["rating"] == 4
    assert mine_b[0]["listing"]["id"] == listing_b


# ── Reviews: deleted item behaviour ───────────────────────────────────────


async def test_review_survives_listing_deletion(client):
    farmer, listing_id = await _farmer_with_listing(client, _phone(64))
    buyer = await _register(client, _phone(65))
    review = await client.post(
        "/api/v1/marketplace/reviews",
        json={"listing_id": listing_id, "rating": 5, "content": "wonderful"},
        headers=buyer,
    )
    review_id = review.json()["id"]
    assert (
        await client.delete(f"/api/v1/marketplace/crops/{listing_id}", headers=farmer)
    ).status_code == 204

    async with async_session_factory() as db:
        farmer_id = await _user_id(db, _phone(64))

    # Review history survives the item being retired — still visible under the
    # seller scope, rendering without a target link.
    seller_reviews = (
        await client.get(
            "/api/v1/marketplace/reviews",
            params={"seller_id": farmer_id},
            headers=buyer,
        )
    ).json()
    assert seller_reviews["total"] == 1
    assert seller_reviews["summary"]["average"] == 5.0
    item = seller_reviews["items"][0]
    assert item["id"] == review_id
    assert item["listing"] is None
    assert item["content"] == "wonderful"


async def test_review_survives_product_deletion(client):
    seller, product_id = await _seller_with_product(client, _phone(66))
    buyer = await _register(client, _phone(67))
    review = await client.post(
        "/api/v1/marketplace/reviews",
        json={"product_id": product_id, "rating": 4, "content": "useful"},
        headers=buyer,
    )
    review_id = review.json()["id"]
    assert (
        await client.delete(f"/api/v1/marketplace/shop/products/{product_id}", headers=seller)
    ).status_code == 204

    async with async_session_factory() as db:
        seller_id = await _user_id(db, _phone(66))

    seller_reviews = (
        await client.get(
            "/api/v1/marketplace/reviews",
            params={"seller_id": seller_id},
            headers=buyer,
        )
    ).json()
    assert seller_reviews["total"] == 1
    assert seller_reviews["summary"]["average"] == 4.0
    assert seller_reviews["items"][0]["id"] == review_id
    assert seller_reviews["items"][0]["product"] is None
