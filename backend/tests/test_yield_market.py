"""Tests for farmer-history yield estimates and attributable market offers."""

from datetime import date, timedelta

from app.db.seed import seed_catalog, seed_crop_calendar
from app.db.session import async_session_factory
from app.models.calendar import CropSchedule
from app.models.catalog import Crop
from app.models.marketplace import CropListing
from sqlalchemy import select


async def _register(client, phone: str) -> tuple[int, dict[str, str]]:
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "phone": phone,
            "name": "Yield Tester",
            "role": "farmer",
            "password": "secret123",
        },
    )
    assert response.status_code == 201, response.text
    token = response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    me = await client.get("/api/v1/auth/me", headers=headers)
    return int(me.json()["id"]), headers


async def test_yield_estimate_requires_actual_harvest_history(client):
    _, headers = await _register(client, "+919100000001")
    async with async_session_factory() as db:
        await seed_catalog(db)
        crop = await db.scalar(select(Crop).where(Crop.name == "tomato"))
        assert crop is not None
        crop_id = crop.id
        growth_days = crop.growth_days

    response = await client.post(
        "/api/v1/yield/estimates",
        headers=headers,
        json={
            "crop_id": crop_id,
            "area_hectares": 0.5,
            "planting_date": date(2026, 1, 1).isoformat(),
        },
    )
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["estimated_yield_kg"] is None
    assert result["historical_harvest_count"] == 0
    assert result["reliability"] == "unavailable"
    assert (
        result["expected_harvest_date"]
        == (date(2026, 1, 1) + timedelta(days=growth_days)).isoformat()
    )
    assert result["is_actual_harvest"] is False
    assert any("actual harvest" in missing for missing in result["missing_inputs"])


async def test_yield_estimate_uses_only_owned_harvest_records(client):
    user_id, headers = await _register(client, "+919100000002")
    async with async_session_factory() as db:
        await seed_catalog(db)
        await seed_crop_calendar(db)
        crop = await db.scalar(select(Crop).where(Crop.name == "tomato"))
        assert crop is not None
        schedule = CropSchedule(
            user_id=user_id,
            crop_id=crop.id,
            planting_date=date(2025, 1, 1),
        )
        db.add(schedule)
        await db.commit()
        schedule_id = schedule.id

    for mass in (1000.0, 1500.0, 2000.0):
        response = await client.post(
            "/api/v1/yield/harvests",
            headers=headers,
            json={
                "schedule_id": schedule_id,
                "actual_yield_kg": mass,
                "area_hectares": 1.0,
                "harvested_on": "2025-06-01",
            },
        )
        assert response.status_code == 201, response.text

    estimate = await client.post(
        "/api/v1/yield/estimates",
        headers=headers,
        json={
            "crop_id": crop.id,
            "area_hectares": 2.0,
            "planting_date": "2026-01-01",
        },
    )
    assert estimate.status_code == 200, estimate.text
    assert estimate.json()["estimated_yield_kg"] == 3000.0
    assert estimate.json()["historical_harvest_count"] == 3
    assert estimate.json()["reliability"] == "moderate"

    harvests = await client.get("/api/v1/yield/harvests", headers=headers)
    assert harvests.status_code == 200
    assert len(harvests.json()) == 3
    assert all(record["actual_yield_kg"] > 0 for record in harvests.json())


async def test_harvest_record_and_estimate_enforce_schedule_ownership(client):
    owner_id, owner_headers = await _register(client, "+919100000003")
    _, other_headers = await _register(client, "+919100000004")
    async with async_session_factory() as db:
        await seed_catalog(db)
        crop = await db.scalar(select(Crop).where(Crop.name == "tomato"))
        assert crop is not None
        schedule = CropSchedule(
            user_id=owner_id,
            crop_id=crop.id,
            planting_date=date(2025, 1, 1),
        )
        db.add(schedule)
        await db.commit()
        schedule_id = schedule.id

    response = await client.post(
        "/api/v1/yield/harvests",
        headers=other_headers,
        json={
            "schedule_id": schedule_id,
            "actual_yield_kg": 100,
            "area_hectares": 1,
            "harvested_on": "2025-06-01",
        },
    )
    assert response.status_code == 404
    assert (
        await client.post(
            "/api/v1/yield/estimates",
            headers=other_headers,
            json={"crop_id": crop.id, "area_hectares": 1, "planting_date": "2026-01-01"},
        )
    ).status_code == 200
    owner_estimate = await client.post(
        "/api/v1/yield/estimates",
        headers=owner_headers,
        json={"crop_id": crop.id, "area_hectares": 1, "planting_date": "2026-01-01"},
    )
    assert owner_estimate.status_code == 200
    assert owner_estimate.json()["historical_harvest_count"] == 0


async def test_market_prices_compare_only_available_crop_offers(client):
    user_id, headers = await _register(client, "+919100000005")
    async with async_session_factory() as db:
        db.add_all(
            [
                CropListing(
                    farmer_id=user_id,
                    crop_name="Tomato",
                    category="vegetable",
                    quantity=100,
                    unit="kg",
                    price=24,
                    location="Pune",
                    availability="available",
                ),
                CropListing(
                    farmer_id=user_id,
                    crop_name="tomato",
                    category="vegetable",
                    quantity=50,
                    unit="kg",
                    price=30,
                    location="Nashik",
                    availability="limited",
                ),
                CropListing(
                    farmer_id=user_id,
                    crop_name="tomato",
                    category="vegetable",
                    quantity=25,
                    unit="kg",
                    price=18,
                    location="Pune",
                    availability="sold_out",
                ),
            ]
        )
        await db.commit()

    response = await client.get(
        "/api/v1/market/prices?crop_name=tomato&page=1&page_size=1",
        headers=headers,
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["total"] == 2
    assert body["pages"] == 2
    assert len(body["items"]) == 1
    assert all(offer["source"] == "farmer-marketplace-listings" for offer in body["items"])
    assert {row["location"] for row in body["comparisons"]} == {"Pune", "Nashik"}
    assert "not official mandi prices" in body["current_offer_note"]
    assert body["historical_trend_available"] is False
    assert body["last_updated_at"] is not None


async def test_market_prices_are_authenticated_and_filter_location(client):
    user_id, headers = await _register(client, "+919100000006")
    async with async_session_factory() as db:
        db.add(
            CropListing(
                farmer_id=user_id,
                crop_name="wheat",
                category="grain",
                quantity=10,
                unit="kg",
                price=21,
                location="Punjab",
                availability="available",
            )
        )
        await db.commit()

    assert (await client.get("/api/v1/market/prices?crop_name=wheat")).status_code == 401
    response = await client.get(
        "/api/v1/market/prices?crop_name=wheat&location=Punjab",
        headers=headers,
    )
    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert response.json()["items"][0]["location"] == "Punjab"
    empty = await client.get(
        "/api/v1/market/prices?crop_name=millet",
        headers=headers,
    )
    assert empty.status_code == 200
    assert empty.json()["items"] == []
    assert "No currently available farmer offers" in empty.json()["current_offer_note"]
