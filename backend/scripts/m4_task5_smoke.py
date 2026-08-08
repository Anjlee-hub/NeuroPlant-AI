"""M4 Task 5 — buyer↔seller messaging end-to-end API smoke journey.

Walks the complete messaging journey against a live backend:
register seller -> register shop -> create product -> register buyer ->
create conversation (product context + opening message) -> duplicate create
reuses the same thread -> seller inbox (unread + preview) -> seller detail ->
seller reply -> buyer mark-read -> close -> messaging blocked (409) ->
reopen -> message again -> RBAC/isolation guards (outsider buyer gets 404).

Run with the live backend reachable at BASE (start: uvicorn app.main:app --port 8001).
Best against a disposable DB (the script registers fresh users):
    DATABASE_URL=sqlite+aiosqlite:///./neuroplant-smoke.db \\
        ./.venv/Scripts/python.exe -m alembic upgrade head
    ./.venv/Scripts/python.exe scripts/m4_task5_smoke.py
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


def _phone() -> str:
    return f"9{str(uuid.uuid4().int)[:9]}"


def main() -> None:
    client = httpx.Client(base_url=API, timeout=30)

    # ── Pre-flight ─────────────────────────────────────────────────────────
    r = client.get(f"{BASE}/ready")
    check("GET /ready", r.status_code == 200, r.text)

    # ── Seller: user + shop + product ──────────────────────────────────────
    seller_phone = _phone()
    r = client.post(
        "/auth/register",
        json={
            "phone": seller_phone,
            "name": "Seller Messaging",
            "role": "seller",
            "password": "secret123",
        },
    )
    check("seller register (201)", r.status_code == 201, f"{r.status_code}: {r.text[:200]}")
    seller_headers = {"Authorization": f"Bearer {r.json()['access_token']}"}

    r = client.post(
        "/marketplace/shop/register",
        json={"shop_name": "Green Agri Supplies", "delivery_available": True},
        headers=seller_headers,
    )
    check("shop register (200)", r.status_code == 200, f"{r.status_code}: {r.text[:200]}")

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
        headers=seller_headers,
    )
    check("create product (201)", r.status_code == 201, f"{r.status_code}: {r.text[:200]}")
    product_id = r.json()["id"]

    # ── Buyer: user + conversation (product context) ───────────────────────
    buyer_phone = _phone()
    r = client.post(
        "/auth/register",
        json={
            "phone": buyer_phone,
            "name": "Buyer Messaging",
            "role": "customer",
            "password": "secret123",
        },
    )
    check("buyer register (201)", r.status_code == 201, r.text[:200])
    buyer_headers = {"Authorization": f"Bearer {r.json()['access_token']}"}

    r = client.post(
        "/marketplace/conversations",
        json={"product_id": product_id, "message": "Is this neem oil in stock?"},
        headers=buyer_headers,
    )
    check("create conversation (201)", r.status_code == 201, f"{r.status_code}: {r.text[:300]}")
    body = r.json()
    conversation_id = body["id"]
    check("conversation references product", body.get("product", {}).get("id") == product_id, body)
    check(
        "conversation seller is the shop",
        body.get("seller", {}).get("shop_name") == "Green Agri Supplies",
        body.get("seller"),
    )
    check(
        "opening message persisted",
        body.get("messages") and body["messages"][0]["content"] == "Is this neem oil in stock?",
        body.get("messages"),
    )
    check("buyer has no unread", body.get("unread_count") == 0, body)

    # Duplicate "Contact Seller" reuses the same thread (no stacked duplicates).
    r = client.post(
        "/marketplace/conversations",
        json={"product_id": product_id, "message": "Actually, do you deliver?"},
        headers=buyer_headers,
    )
    check(
        "duplicate create reuses thread",
        r.status_code == 201 and r.json()["id"] == conversation_id,
        f"{r.status_code}: {r.text[:200]}",
    )
    check("second message appended", len(r.json()["messages"]) == 2, r.json().get("messages"))

    # ── Seller side: inbox → detail → reply ───────────────────────────────
    r = client.get("/marketplace/conversations", headers=seller_headers)
    inbox = r.json()
    check(
        "seller inbox has 1 thread",
        r.status_code == 200 and len(inbox) == 1,
        f"{r.status_code}: {r.text[:300]}",
    )
    check("seller inbox unread = 2", inbox[0]["unread_count"] == 2, inbox)
    check(
        "seller inbox preview",
        inbox[0]["last_message_preview"].startswith("Actually, do you deliver?"),
        inbox[0],
    )

    r = client.get(f"/marketplace/conversations/{conversation_id}", headers=seller_headers)
    check(
        "seller detail (200)",
        r.status_code == 200 and len(r.json()["messages"]) == 2,
        f"{r.status_code}: {r.text[:200]}",
    )
    check("seller detail unread = 2", r.json()["unread_count"] == 2, r.json())

    r = client.post(
        f"/marketplace/conversations/{conversation_id}/messages",
        json={"content": "Yes — and we deliver across Ludhiana."},
        headers=seller_headers,
    )
    check("seller reply (201)", r.status_code == 201, f"{r.status_code}: {r.text[:200]}")
    check("reply sender is the seller", r.json()["sender_id"] == body["seller"]["id"], r.json())

    # Buyer reads → unread clears, read_at stamped.
    r = client.get(f"/marketplace/conversations/{conversation_id}", headers=buyer_headers)
    check("buyer unread after reply = 1", r.json()["unread_count"] == 1, r.json())
    r = client.post(f"/marketplace/conversations/{conversation_id}/read", headers=buyer_headers)
    check(
        "mark read (200, 0 unread)", r.status_code == 200 and r.json()["unread_count"] == 0, r.text
    )
    r = client.get(f"/marketplace/conversations/{conversation_id}", headers=buyer_headers)
    check(
        "reply marked read_at",
        r.json()["messages"][-1]["read_at"] is not None,
        r.json()["messages"][-1],
    )

    # ── Close → blocked → reopen ──────────────────────────────────────────
    r = client.post(f"/marketplace/conversations/{conversation_id}/close", headers=buyer_headers)
    check(
        "close (200, closed)",
        r.status_code == 200 and r.json()["status"] == "closed",
        f"{r.status_code}: {r.text[:200]}",
    )
    r = client.post(
        f"/marketplace/conversations/{conversation_id}/messages",
        json={"content": "still here?"},
        headers=buyer_headers,
    )
    check(
        "message on closed thread blocked (409)",
        r.status_code == 409,
        f"{r.status_code}: {r.text[:200]}",
    )
    r = client.post(
        "/marketplace/conversations",
        json={"product_id": product_id, "message": "Reopening this thread."},
        headers=buyer_headers,
    )
    check(
        "contact reopens same thread",
        r.status_code == 201
        and r.json()["id"] == conversation_id
        and r.json()["status"] == "active",
        f"{r.status_code}: {r.text[:200]}",
    )
    r = client.post(
        f"/marketplace/conversations/{conversation_id}/messages",
        json={"content": "Great, send me two bottles."},
        headers=buyer_headers,
    )
    check("message after reopen (201)", r.status_code == 201, f"{r.status_code}: {r.text[:200]}")

    # ── Isolation guards ──────────────────────────────────────────────────
    outsider_phone = _phone()
    r = client.post(
        "/auth/register",
        json={
            "phone": outsider_phone,
            "name": "Outsider",
            "role": "customer",
            "password": "secret123",
        },
    )
    outsider_headers = {"Authorization": f"Bearer {r.json()['access_token']}"}
    r = client.get(f"/marketplace/conversations/{conversation_id}", headers=outsider_headers)
    check(
        "outsider cannot read thread (404)",
        r.status_code == 404,
        f"{r.status_code}: {r.text[:200]}",
    )
    r = client.post(
        f"/marketplace/conversations/{conversation_id}/messages",
        json={"content": "sneak"},
        headers=outsider_headers,
    )
    check(
        "outsider cannot message thread (404)",
        r.status_code == 404,
        f"{r.status_code}: {r.text[:200]}",
    )
    r = client.get("/marketplace/conversations", headers=outsider_headers)
    check("outsider inbox is empty", r.status_code == 200 and r.json() == [], r.text[:200])
    r = client.get("/marketplace/conversations/999999", headers=buyer_headers)
    check("missing conversation (404)", r.status_code == 404, f"{r.status_code}: {r.text[:200]}")

    # ── Summary ────────────────────────────────────────────────────────────
    print(f"\n{len(passed)} passed, {len(failed)} failed")
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
