"""Grounded government scheme discovery and eligibility tests."""

from app.db.session import async_session_factory
from app.models.scheme import SchemeUsageEvent
from app.models.user import User
from sqlalchemy import select


async def _register(client, phone: str) -> tuple[int, dict[str, str]]:
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "phone": phone,
            "name": "Scheme Tester",
            "role": "farmer",
            "password": "secret123",
        },
    )
    assert response.status_code == 201, response.text
    headers = {"Authorization": f"Bearer {response.json()['access_token']}"}
    me = await client.get("/api/v1/auth/me", headers=headers)
    return int(me.json()["id"]), headers


async def _make_admin(user_id: int) -> None:
    async with async_session_factory() as db:
        user = await db.get(User, user_id)
        assert user is not None
        user.role = "admin"
        await db.commit()


async def test_scheme_catalog_reports_empty_data_without_fabrication(client):
    _, headers = await _register(client, "+919200000001")
    response = await client.get("/api/v1/schemes", headers=headers)
    assert response.status_code == 200
    assert response.json()["items"] == []
    assert response.json()["total"] == 0
    assert response.json()["source_status"] == "no_scheme_records"


async def test_admin_can_add_verified_source_and_farmers_can_filter_and_check(client):
    user_id, headers = await _register(client, "+919200000002")
    await _make_admin(user_id)
    create = await client.post(
        "/api/v1/schemes",
        headers=headers,
        json={
            "name": "Test verified scheme",
            "category": "irrigation",
            "description": "A test description from a source record.",
            "benefits": "Published benefits",
            "state_codes": ["KA"],
            "crops": ["rice"],
            "farmer_categories": ["small"],
            "eligibility_requirements": ["Applicant must meet the published rules."],
            "eligibility_rules": {
                "state_code": ["KA"],
                "crop_name": ["rice"],
                "farmer_category": ["small"],
            },
            "required_documents": ["Identity proof"],
            "application_instructions": "Follow the official instructions.",
            "official_application_url": "https://example.gov/apply",
            "subsidy_details": "Amount as stated in source.",
            "source_name": "Test source",
            "source_url": "https://example.gov/scheme",
            "last_verified_at": "2026-10-01T00:00:00Z",
            "is_verified": True,
        },
    )
    assert create.status_code == 201, create.text
    scheme_id = create.json()["id"]

    details = await client.get(f"/api/v1/schemes/{scheme_id}", headers=headers)
    assert details.status_code == 200
    assert details.json()["description"] == "A test description from a source record."
    assert details.json()["required_documents"] == ["Identity proof"]
    assert details.json()["application_instructions"] == "Follow the official instructions."
    assert details.json()["source_url"] == "https://example.gov/scheme"

    listing = await client.get(
        "/api/v1/schemes?state_code=KA&crop_name=rice&farmer_category=small",
        headers=headers,
    )
    assert listing.status_code == 200
    assert listing.json()["total"] == 1
    assert listing.json()["items"][0]["is_verified"] is True
    assert listing.json()["items"][0]["official_application_url"] == "https://example.gov/apply"
    assert listing.json()["items"][0]["source_name"] == "Test source"
    assert listing.json()["items"][0]["source_url"] == "https://example.gov/scheme"

    eligibility = await client.post(
        f"/api/v1/schemes/{scheme_id}/eligibility",
        headers=headers,
        json={"state_code": "KA", "crop_name": "rice", "farmer_category": "small"},
    )
    assert eligibility.status_code == 200
    assert eligibility.json()["outcome"] == "potentially_eligible"
    assert eligibility.json()["legal_determination"] is False

    mismatch = await client.post(
        f"/api/v1/schemes/{scheme_id}/eligibility",
        headers=headers,
        json={"state_code": "TN", "crop_name": "rice", "farmer_category": "small"},
    )
    assert mismatch.json()["outcome"] == "not_eligible"
    async with async_session_factory() as db:
        actions = list(
            await db.scalars(
                select(SchemeUsageEvent.action).where(
                    SchemeUsageEvent.scheme_id == scheme_id,
                    SchemeUsageEvent.user_id == user_id,
                )
            )
        )
    assert actions.count("view") >= 1
    assert actions.count("eligibility_check") == 2


async def test_unknown_eligibility_and_unverified_scheme_hide_financial_links(client):
    user_id, headers = await _register(client, "+919200000003")
    await _make_admin(user_id)
    created = await client.post(
        "/api/v1/schemes",
        headers=headers,
        json={
            "name": "Unverified draft",
            "category": "general",
            "description": "Draft only; not verified.",
            "subsidy_details": "Unverified amount not displayed.",
            "official_application_url": "https://example.gov/unverified",
            "source_name": "Unverified source",
            "source_url": "https://example.gov/draft",
            "is_verified": False,
        },
    )
    assert created.status_code == 201, created.text
    scheme_id = created.json()["id"]
    assert created.json()["official_application_url"] is None
    assert created.json()["subsidy_details"] is None
    assert created.json()["is_verified"] is False

    result = await client.post(
        f"/api/v1/schemes/{scheme_id}/eligibility",
        headers=headers,
        json={},
    )
    assert result.status_code == 200
    assert result.json()["outcome"] == "unknown"


async def test_scheme_administration_requires_admin_role(client):
    _, headers = await _register(client, "+919200000004")
    response = await client.post(
        "/api/v1/schemes",
        headers=headers,
        json={
            "name": "Not allowed",
            "category": "general",
            "description": "Test",
            "source_name": "Test",
            "source_url": "https://example.gov/source",
        },
    )
    assert response.status_code == 403


async def test_save_status_list_and_remove_scheme(client):
    user_id, headers = await _register(client, "+919200000005")
    await _make_admin(user_id)
    created = await client.post(
        "/api/v1/schemes",
        headers=headers,
        json={
            "name": "Saved catalogue scheme",
            "category": "storage",
            "department": "Test Department",
            "description": "Officially attributed test record.",
            "state_codes": ["KA"],
            "district_codes": ["Bengaluru Urban"],
            "source_name": "Test department",
            "source_url": "https://example.gov/saved-catalogue-scheme",
        },
    )
    assert created.status_code == 201, created.text
    scheme_id = created.json()["id"]

    initial_status = await client.get(
        f"/api/v1/schemes/saved/status/{scheme_id}",
        headers=headers,
    )
    assert initial_status.json() == {"saved": False}

    save = await client.post(
        f"/api/v1/schemes/saved/{scheme_id}",
        headers=headers,
    )
    assert save.status_code == 200
    assert save.json() == {"saved": True}

    saved = await client.get("/api/v1/schemes/saved", headers=headers)
    assert saved.status_code == 200
    assert [item["id"] for item in saved.json()] == [scheme_id]

    remove = await client.delete(
        f"/api/v1/schemes/saved/{scheme_id}",
        headers=headers,
    )
    assert remove.status_code == 200
    assert remove.json() == {"saved": False}
    remaining = await client.get("/api/v1/schemes/saved", headers=headers)
    assert remaining.json() == []


async def test_saved_schemes_are_isolated_by_authenticated_user(client):
    owner_id, owner_headers = await _register(client, "+919200000007")
    await _make_admin(owner_id)
    created = await client.post(
        "/api/v1/schemes",
        headers=owner_headers,
        json={
            "name": "Private saved scheme",
            "category": "storage",
            "description": "A source-attributed test record.",
            "source_name": "Test department",
            "source_url": "https://example.gov/private-saved-scheme",
        },
    )
    assert created.status_code == 201, created.text
    scheme_id = created.json()["id"]
    assert (await client.post(
        f"/api/v1/schemes/saved/{scheme_id}",
        headers=owner_headers,
    )).status_code == 200

    _, other_headers = await _register(client, "+919200000008")
    status = await client.get(
        f"/api/v1/schemes/saved/status/{scheme_id}",
        headers=other_headers,
    )
    saved = await client.get("/api/v1/schemes/saved", headers=other_headers)
    remove = await client.delete(
        f"/api/v1/schemes/saved/{scheme_id}",
        headers=other_headers,
    )

    assert status.json() == {"saved": False}
    assert saved.json() == []
    assert remove.status_code == 404


async def test_search_and_duplicate_catalogue_records(client):
    user_id, headers = await _register(client, "+919200000006")
    await _make_admin(user_id)
    payload = {
        "name": "District search scheme",
        "category": "irrigation",
        "department": "Test Department",
        "description": "A source-backed irrigation record.",
        "district_codes": ["Bengaluru Rural"],
        "source_name": "Test department",
        "source_url": "https://example.gov/district-search-scheme",
    }
    first = await client.post("/api/v1/schemes", headers=headers, json=payload)
    assert first.status_code == 201

    duplicate = await client.post("/api/v1/schemes", headers=headers, json=payload)
    assert duplicate.status_code == 409

    listing = await client.get(
        "/api/v1/schemes",
        headers=headers,
        params={"district_code": "Bengaluru Rural", "search": "irrigation"},
    )
    assert listing.status_code == 200
    assert listing.json()["total"] == 1
