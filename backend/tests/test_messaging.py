"""M4, Task 5 tests — buyer↔seller messaging.

Covers the inquiry system's full surface: conversation creation (with product /
listing / explicit-seller context), duplicate-reuse, the ownership isolation
guards (a buyer or seller can never reach another party's thread — 404, the
platform's enumeration guard), unauthenticated 401s, message sending + length
validation, mark-read, the closed-conversation lifecycle (reopen, 409 on
messaging a closed thread, idempotent close) and viewer-relative unread counts.
"""

from app.db.session import async_session_factory
from app.models.user import User
from sqlalchemy import select


def _phone(n: int) -> str:
    return f"9{n:010d}"


async def _register(client, phone: str, role: str = "customer") -> dict:
    resp = await client.post(
        "/api/v1/auth/register",
        json={"phone": phone, "name": "Messaging Tester", "role": role, "password": "secret123"},
    )
    assert resp.status_code == 201, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


async def _seller_with_product(
    client, phone: str, shop_name: str = "Green Agri"
) -> tuple[dict, int]:
    """Register a seller, register their shop and create one product."""
    headers = await _register(client, phone, role="seller")
    resp = await client.post(
        "/api/v1/marketplace/shop/register",
        json={"shop_name": shop_name, "delivery_available": True},
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


async def _farmer_with_listing(client, phone: str) -> tuple[dict, int]:
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


async def _create_conversation(client, headers: dict, **context) -> dict:
    """POST a conversation with the given context; returns the created detail."""
    resp = await client.post("/api/v1/marketplace/conversations", json=context, headers=headers)
    assert resp.status_code == 201, resp.text
    return resp.json()


# ── Auth + RBAC ───────────────────────────────────────────────────────────


async def test_unauthenticated_cannot_access_messaging(client):
    endpoints = [
        ("get", "/api/v1/marketplace/conversations"),
        ("get", "/api/v1/marketplace/conversations/1"),
        ("post", "/api/v1/marketplace/conversations"),
        ("post", "/api/v1/marketplace/conversations/1/messages"),
        ("post", "/api/v1/marketplace/conversations/1/read"),
        ("post", "/api/v1/marketplace/conversations/1/close"),
    ]
    for method, url in endpoints:
        resp = await client.request(method, url, json={"content": "hi"})
        assert resp.status_code == 401, (method, url, resp.text)


# ── Create + duplicate reuse ──────────────────────────────────────────────


async def test_buyer_creates_product_conversation(client):
    seller_headers, product_id = await _seller_with_product(client, _phone(1))
    buyer = await _register(client, _phone(2))
    body = await _create_conversation(
        client, buyer, product_id=product_id, message="Is this in stock?"
    )

    assert body["status"] == "active"
    assert body["product"]["id"] == product_id
    assert body["product"]["name"] == "Neem Oil"
    assert body["listing"] is None
    assert body["buyer"]["role"] == "customer"
    assert body["seller"]["shop_name"] == "Green Agri"
    assert len(body["messages"]) == 1
    assert body["messages"][0]["content"] == "Is this in stock?"
    assert body["messages"][0]["sender_name"] == "Messaging Tester"
    assert body["unread_count"] == 0  # own messages never count as unread

    # The seller sees it in their inbox as unread.
    inbox = await client.get("/api/v1/marketplace/conversations", headers=seller_headers)
    rows = inbox.json()
    assert inbox.status_code == 200 and len(rows) == 1
    assert rows[0]["id"] == body["id"]
    assert rows[0]["unread_count"] == 1
    assert rows[0]["last_message_preview"] == "Is this in stock?"
    assert rows[0]["status"] == "active"


async def test_duplicate_create_reuses_same_conversation(client):
    _, product_id = await _seller_with_product(client, _phone(3))
    buyer = await _register(client, _phone(4))

    first = await _create_conversation(client, buyer, product_id=product_id, message="Hello")
    second = await _create_conversation(client, buyer, product_id=product_id, message="Hello again")

    assert second["id"] == first["id"]
    # Reuse keeps the single thread: history preserved, second message appended.
    assert [m["content"] for m in second["messages"]] == ["Hello", "Hello again"]
    assert second["status"] == "active"


async def test_create_with_listing_uses_listing_farmer(client):
    farmer_headers, listing_id = await _farmer_with_listing(client, _phone(5))
    buyer = await _register(client, _phone(6))
    body = await _create_conversation(
        client, buyer, listing_id=listing_id, message="Price negotiable?"
    )

    assert body["listing"]["id"] == listing_id
    assert body["listing"]["crop_name"] == "Organic Tomato"
    assert body["product"] is None
    # The seller side is the listing's farmer.
    async with async_session_factory() as db:
        farmer = await db.scalar(select(User).where(User.phone == _phone(5)))
        assert farmer is not None
        assert body["seller"]["id"] == farmer.id
        assert body["buyer"]["id"] != farmer.id


async def test_create_with_explicit_seller_id(client):
    seller_headers, _ = await _seller_with_product(client, _phone(7))
    async with async_session_factory() as db:
        seller = await db.scalar(select(User).where(User.phone == _phone(7)))
        assert seller is not None
    buyer = await _register(client, _phone(8))
    body = await _create_conversation(client, buyer, seller_id=seller.id)
    assert body["seller"]["id"] == seller.id
    assert body["listing"] is None and body["product"] is None
    assert body["messages"] == []  # no opening message → empty thread


async def test_self_contact_rejected(client):
    seller_headers, product_id = await _seller_with_product(client, _phone(9))
    resp = await client.post(
        "/api/v1/marketplace/conversations",
        json={"product_id": product_id, "message": "hi"},
        headers=seller_headers,
    )
    assert resp.status_code == 400


async def test_context_selection_is_enforced(client):
    buyer = await _register(client, _phone(10))
    seller_headers, product_id = await _seller_with_product(client, _phone(11))
    async with async_session_factory() as db:
        seller = await db.scalar(select(User).where(User.phone == _phone(11)))
        assert seller is not None

    # Both listing + product → 400.
    resp = await client.post(
        "/api/v1/marketplace/conversations",
        json={"seller_id": seller.id, "product_id": product_id},
        headers=buyer,
    )
    assert resp.status_code == 400
    # None at all → 400.
    resp = await client.post(
        "/api/v1/marketplace/conversations", json={"message": "hi"}, headers=buyer
    )
    assert resp.status_code == 400
    # Unknown references → 400 (never a leak).
    resp = await client.post(
        "/api/v1/marketplace/conversations",
        json={"product_id": 999999},
        headers=buyer,
    )
    assert resp.status_code == 400


# ── Ownership isolation (IDOR guards) ─────────────────────────────────────


async def test_buyer_cannot_access_another_buyers_conversation(client):
    _, product_id = await _seller_with_product(client, _phone(12))
    buyer_a = await _register(client, _phone(13))
    buyer_b = await _register(client, _phone(14))
    created = await _create_conversation(client, buyer_a, product_id=product_id)

    detail = await client.get(f"/api/v1/marketplace/conversations/{created['id']}", headers=buyer_b)
    assert detail.status_code == 404
    send = await client.post(
        f"/api/v1/marketplace/conversations/{created['id']}/messages",
        json={"content": "sneak"},
        headers=buyer_b,
    )
    assert send.status_code == 404
    read = await client.post(
        f"/api/v1/marketplace/conversations/{created['id']}/read", headers=buyer_b
    )
    assert read.status_code == 404
    close = await client.post(
        f"/api/v1/marketplace/conversations/{created['id']}/close", headers=buyer_b
    )
    assert close.status_code == 404

    # Buyer A's own access is unaffected.
    assert (
        await client.get(f"/api/v1/marketplace/conversations/{created['id']}", headers=buyer_a)
    ).status_code == 200


async def test_seller_cannot_access_another_sellers_conversation(client):
    seller_a_headers, product_a = await _seller_with_product(client, _phone(15), shop_name="Shop A")
    seller_b_headers, _ = await _seller_with_product(client, _phone(16), shop_name="Shop B")
    buyer = await _register(client, _phone(17))
    created = await _create_conversation(client, buyer, product_id=product_a)

    detail = await client.get(
        f"/api/v1/marketplace/conversations/{created['id']}", headers=seller_b_headers
    )
    assert detail.status_code == 404
    send = await client.post(
        f"/api/v1/marketplace/conversations/{created['id']}/messages",
        json={"content": "hi"},
        headers=seller_b_headers,
    )
    assert send.status_code == 404
    # The actual seller can reply.
    reply = await client.post(
        f"/api/v1/marketplace/conversations/{created['id']}/messages",
        json={"content": "In stock"},
        headers=seller_a_headers,
    )
    assert reply.status_code == 201


async def test_missing_conversation_is_404(client):
    buyer = await _register(client, _phone(18))
    resp = await client.get("/api/v1/marketplace/conversations/999999", headers=buyer)
    assert resp.status_code == 404


async def test_inbox_is_participant_scoped(client):
    _, product_a = await _seller_with_product(client, _phone(19))
    buyer_a = await _register(client, _phone(20))
    buyer_b = await _register(client, _phone(21))
    await _create_conversation(client, buyer_a, product_id=product_a)

    assert (
        await client.get("/api/v1/marketplace/conversations", headers=buyer_a)
    ).json().__len__() == 1
    assert (await client.get("/api/v1/marketplace/conversations", headers=buyer_b)).json() == []


# ── Send / read / close lifecycle ─────────────────────────────────────────


async def test_send_reply_and_mark_read_flow(client):
    seller_headers, product_id = await _seller_with_product(client, _phone(22))
    buyer = await _register(client, _phone(23))
    created = await _create_conversation(client, buyer, product_id=product_id, message="Available?")

    conversation_id = created["id"]
    # Seller replies → buyer's unread goes up.
    reply = await client.post(
        f"/api/v1/marketplace/conversations/{conversation_id}/messages",
        json={"content": "Yes, 40 litres left."},
        headers=seller_headers,
    )
    assert reply.status_code == 201
    body = reply.json()
    assert body["sender_id"] == created["seller"]["id"]
    assert body["read_at"] is None
    assert body["sender_name"] == "Messaging Tester"

    # Buyer's detail shows the reply as unread (seller's turn, buyer unread).
    detail = await client.get(f"/api/v1/marketplace/conversations/{conversation_id}", headers=buyer)
    assert detail.json()["unread_count"] == 1

    # Buyer marks read → unread 0, read_at stamped.
    read = await client.post(
        f"/api/v1/marketplace/conversations/{conversation_id}/read", headers=buyer
    )
    assert read.status_code == 200
    assert read.json()["unread_count"] == 0
    detail = await client.get(f"/api/v1/marketplace/conversations/{conversation_id}", headers=buyer)
    assert detail.json()["unread_count"] == 0
    messages = detail.json()["messages"]
    assert messages[-1]["read_at"] is not None
    # The seller's own message doesn't get stamped by the buyer's read.
    assert messages[0]["read_at"] is None


async def test_message_validation(client):
    seller_headers, product_id = await _seller_with_product(client, _phone(24))
    buyer = await _register(client, _phone(25))
    created = await _create_conversation(client, buyer, product_id=product_id)

    # Empty content → 422.
    resp = await client.post(
        f"/api/v1/marketplace/conversations/{created['id']}/messages",
        json={"content": ""},
        headers=buyer,
    )
    assert resp.status_code == 422
    # Over the 2000-char limit → 422.
    resp = await client.post(
        f"/api/v1/marketplace/conversations/{created['id']}/messages",
        json={"content": "x" * 2001},
        headers=buyer,
    )
    assert resp.status_code == 422
    # Whitespace-only content is rejected by the min_length validator.
    resp = await client.post(
        f"/api/v1/marketplace/conversations/{created['id']}/messages",
        json={"content": "   "},
        headers=buyer,
    )
    assert resp.status_code == 422
    # Opening message over the limit is rejected at create time too.
    resp = await client.post(
        "/api/v1/marketplace/conversations",
        json={"product_id": product_id, "message": "y" * 2001},
        headers=buyer,
    )
    assert resp.status_code == 422


async def test_closed_conversation_blocks_and_reopens(client):
    seller_headers, product_id = await _seller_with_product(client, _phone(26))
    buyer = await _register(client, _phone(27))
    created = await _create_conversation(client, buyer, product_id=product_id, message="Hello")
    conversation_id = created["id"]

    # Close → status closed, history stays.
    closed = await client.post(
        f"/api/v1/marketplace/conversations/{conversation_id}/close", headers=buyer
    )
    assert closed.status_code == 200
    assert closed.json()["status"] == "closed"

    # Messages are rejected on a closed thread (409) for both sides.
    for headers in (buyer, seller_headers):
        resp = await client.post(
            f"/api/v1/marketplace/conversations/{conversation_id}/messages",
            json={"content": "late reply"},
            headers=headers,
        )
        assert resp.status_code == 409, resp.text

    # Closing again is idempotent.
    again = await client.post(
        f"/api/v1/marketplace/conversations/{conversation_id}/close", headers=seller_headers
    )
    assert again.status_code == 200 and again.json()["status"] == "closed"

    # A fresh "Contact Seller" reopens the same thread (no duplicate) with history.
    reopened = await _create_conversation(
        client, buyer, product_id=product_id, message="Back again"
    )
    assert reopened["id"] == conversation_id
    assert reopened["status"] == "active"
    assert [m["content"] for m in reopened["messages"]] == ["Hello", "Back again"]
    # And messaging works again.
    resp = await client.post(
        f"/api/v1/marketplace/conversations/{conversation_id}/messages",
        json={"content": "thanks"},
        headers=buyer,
    )
    assert resp.status_code == 201


async def test_list_sorts_newest_activity_first(client):
    seller_headers, product_id = await _seller_with_product(client, _phone(28))
    buyer = await _register(client, _phone(29))
    first = await _create_conversation(client, buyer, product_id=product_id, message="First thread")

    # A second context (explicit seller id) starts a second thread.
    async with async_session_factory() as db:
        seller = await db.scalar(select(User).where(User.phone == _phone(28)))
        assert seller is not None
    second = await _create_conversation(client, buyer, seller_id=seller.id, message="Second thread")

    # Buyer's inbox: second thread has the newer activity → first.
    inbox = (await client.get("/api/v1/marketplace/conversations", headers=buyer)).json()
    assert [row["id"] for row in inbox] == [second["id"], first["id"]]
    assert inbox[0]["last_message_preview"] == "Second thread"
