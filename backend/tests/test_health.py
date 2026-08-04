"""Ops-probe tests (M0)."""


async def test_health(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


async def test_ready_reports_database(client):
    resp = await client.get("/ready")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ready"
    assert body["database"] == "up"


async def test_root_ok(client):
    resp = await client.get("/")
    assert resp.status_code == 200
    assert resp.json()["service"] == "NeuroPlant AI"
