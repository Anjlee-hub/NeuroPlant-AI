"""API tests for the read-only catalog endpoint (M2 Task 7.1 filter support).

``GET /catalog/crops`` feeds the Scan History crop-filter dropdown, so the
contract is pinned: bearer-required, seeded crops, name-ordered, and the
``id | name | common_name`` shape the UI select expects.
"""

from app.db.seed import seed_catalog


async def _auth_headers(client, phone: str) -> dict:
    resp = await client.post(
        "/api/v1/auth/register",
        json={"phone": phone, "name": "Tester", "role": "farmer", "password": "secret123"},
    )
    assert resp.status_code == 201, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


async def test_crops_requires_auth(client):
    resp = await client.get("/api/v1/catalog/crops")
    assert resp.status_code == 401


async def test_crops_lists_seeded_crops(client, db):
    await seed_catalog(db)
    headers = await _auth_headers(client, "+919000000201")
    resp = await client.get("/api/v1/catalog/crops", headers=headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert isinstance(body, list) and len(body) >= 3
    for crop in body:
        assert {"id", "name", "common_name"} <= set(crop)
    # Name-ordered so the dropdown is stable.
    names = [c["name"].lower() for c in body]
    assert names == sorted(names)


async def test_crops_empty_before_seed(client, db):
    headers = await _auth_headers(client, "+919000000202")
    resp = await client.get("/api/v1/catalog/crops", headers=headers)
    assert resp.status_code == 200, resp.text
    assert resp.json() == []
