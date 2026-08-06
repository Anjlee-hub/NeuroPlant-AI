"""M3, Task 6 tests — voice AI assistant.

Covers the rule-based assistant endpoint: auth gating, bilingual intent
routing (English + Hindi keywords, language auto-detection), and every
data-backed intent composing the existing engines — latest-scan disease,
treatment plan (homemade/organic/chemical), fertilizer guidance, disease-aware
soil care, recovery tracker, and today's calendar tasks. Each intent degrades
to a helpful reply (never a 500) when the user has no scans, no disease, or no
curated plan.
"""

import uuid
from datetime import UTC, datetime

from app.db.seed import (
    seed_catalog,
    seed_crop_calendar,
    seed_recommendations,
    seed_soil_recommendations,
)
from app.db.session import async_session_factory
from app.models.catalog import Crop, Disease
from app.models.user import User
from app.schemas.scan import ScanCreate
from app.services.scans import ScanService
from sqlalchemy import select


def _uuid(n: int) -> str:
    return str(uuid.UUID(int=n))


def _utc_today() -> str:
    return datetime.now(UTC).date().isoformat()


async def _seed():
    """Full catalogs: crops/diseases + treatment + soil + calendar."""
    async with async_session_factory() as db:
        await seed_catalog(db)
        await seed_recommendations(db)
        await seed_soil_recommendations(db)
        await seed_crop_calendar(db)


async def _register(client, phone: str) -> dict:
    resp = await client.post(
        "/api/v1/auth/register",
        json={"phone": phone, "name": "Tester", "role": "farmer", "password": "secret123"},
    )
    assert resp.status_code == 201, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


async def _user_id(db, phone: str) -> int:
    user = await db.scalar(select(User).where(User.phone == phone))
    assert user is not None
    return user.id


async def _crop_id(name: str = "tomato") -> int:
    async with async_session_factory() as db:
        crop = await db.scalar(select(Crop).where(Crop.name == name))
        assert crop is not None
        return crop.id


async def _disease_id(crop_name: str, disease_name: str) -> int:
    async with async_session_factory() as db:
        row = await db.scalar(
            select(Disease).join(Crop).where(Crop.name == crop_name, Disease.name == disease_name)
        )
        assert row is not None
        return row.id


async def _make_scan(
    user_id: int,
    *,
    crop_id: int | None = None,
    disease_id: int | None = None,
    disease_name: str = "Early Blight",
    severity: str = "severe",
    confidence: float = 0.92,
    variant: int = 0,
) -> int:
    async with async_session_factory() as db:
        scan = await ScanService(db).create(
            ScanCreate(
                client_scan_id=_uuid(9200 + user_id * 100 + variant),
                user_id=user_id,
                image_path="/media/test.jpg",
                media_items=[],
                crop_id=crop_id,
                part_type="leaf",
                disease_id=disease_id,
                disease_name=disease_name,
                confidence=confidence,
                severity=severity,
                stage="early",
                provider="test",
                model_name="test-model",
                model_version="1.0",
                dataset_version="v1",
                preprocessing_time_ms=1.0,
                inference_time_ms=2.0,
                processing_time_ms=3.0,
                ai_metadata={},
                device_id="test-device",
                synced_at=None,
            )
        )
        return scan.id


async def _ask(client, headers, query: str, lang: str | None = None):
    payload = {"query": query}
    if lang is not None:
        payload["lang"] = lang
    resp = await client.post("/api/v1/assistant", json=payload, headers=headers)
    assert resp.status_code == 200, resp.text
    return resp.json()


# ── Auth + validation ──────────────────────────────────────────────────────


async def test_assistant_requires_auth(client):
    resp = await client.post("/api/v1/assistant", json={"query": "hello"})
    assert resp.status_code == 401


async def test_assistant_validates_empty_query(client):
    await _seed()
    headers = await _register(client, "+919310000001")
    resp = await client.post("/api/v1/assistant", json={"query": ""}, headers=headers)
    assert resp.status_code == 422


async def test_assistant_rejects_unrecognized_lang_gracefully(client):
    await _seed()
    headers = await _register(client, "+919310000002")
    body = await _ask(client, headers, "hello", lang="fr")
    assert body["lang"] == "en"  # unrecognized code falls back to script detection


# ── Static intents (greeting / help / fallback) ───────────────────────────


async def test_greeting_in_english(client):
    await _seed()
    headers = await _register(client, "+919310000003")
    body = await _ask(client, headers, "Hello!")
    assert body["intent"] == "greeting"
    assert body["lang"] == "en"
    assert "NeuroPlant" in body["message"]
    assert body["sections"][0]["title"] == "Try asking"


async def test_hindi_query_auto_detects_language(client):
    await _seed()
    headers = await _register(client, "+919310000004")
    body = await _ask(client, headers, "नमस्ते")
    assert body["intent"] == "greeting"
    assert body["lang"] == "hi"
    assert any("अ" <= ch <= "ॿ" for ch in body["message"])


async def test_unknown_query_returns_fallback(client):
    await _seed()
    headers = await _register(client, "+919310000005")
    body = await _ask(client, headers, "zzzz blorp quux")
    assert body["intent"] == "fallback"
    assert "couldn't find" in body["message"]


# ── Data-backed intents ────────────────────────────────────────────────────


async def test_disease_intent_with_no_scans_guides_to_scan_crop(client):
    await _seed()
    headers = await _register(client, "+919310000006")
    body = await _ask(client, headers, "What disease does my crop have?")
    assert body["intent"] == "disease"
    assert "scan" in body["message"].lower()


async def test_disease_intent_reports_latest_scan(client, db):
    await _seed()
    headers = await _register(client, "+919310000007")
    user_id = await _user_id(db, "+919310000007")
    crop_id = await _crop_id("tomato")
    disease_id = await _disease_id("tomato", "Early Blight")
    await _make_scan(user_id, crop_id=crop_id, disease_id=disease_id)

    body = await _ask(client, headers, "What disease does my crop have?")
    assert body["intent"] == "disease"
    assert "Early Blight" in body["message"]
    assert "92%" in body["message"]
    assert any(s["title"] == "What the scan shows" for s in body["sections"])
    assert any(s["title"] == "Next step" for s in body["sections"])


async def test_disease_intent_healthy_scan(client, db):
    await _seed()
    headers = await _register(client, "+919310000008")
    user_id = await _user_id(db, "+919310000008")
    crop_id = await _crop_id("tomato")
    await _make_scan(user_id, crop_id=crop_id, disease_id=None, disease_name="Healthy")

    body = await _ask(client, headers, "What disease does my crop have?")
    assert body["intent"] == "disease"
    assert "didn't find a disease" in body["message"]


async def test_treatment_intent_lists_remedies(client, db):
    await _seed()
    headers = await _register(client, "+919310000009")
    user_id = await _user_id(db, "+919310000009")
    crop_id = await _crop_id("tomato")
    disease_id = await _disease_id("tomato", "Early Blight")
    await _make_scan(user_id, crop_id=crop_id, disease_id=disease_id)

    body = await _ask(client, headers, "How do I treat this disease?")
    assert body["intent"] == "treatment"
    titles = {s["title"] for s in body["sections"]}
    assert "Homemade remedy" in titles
    assert "Organic remedy" in titles
    assert "Chemical option" in titles


async def test_fertilizer_intent_returns_guidance(client, db):
    await _seed()
    headers = await _register(client, "+919310000010")
    user_id = await _user_id(db, "+919310000010")
    crop_id = await _crop_id("tomato")
    disease_id = await _disease_id("tomato", "Early Blight")
    await _make_scan(user_id, crop_id=crop_id, disease_id=disease_id)

    body = await _ask(client, headers, "What fertilizer should I use?")
    assert body["intent"] == "fertilizer"
    assert body["sections"][0]["title"] == "Fertilizer guidance"
    assert body["sections"][0]["body"].strip()


async def test_soil_intent_returns_health_and_care(client, db):
    await _seed()
    headers = await _register(client, "+919310000011")
    user_id = await _user_id(db, "+919310000011")
    crop_id = await _crop_id("tomato")
    disease_id = await _disease_id("tomato", "Early Blight")
    await _make_scan(user_id, crop_id=crop_id, disease_id=disease_id)

    body = await _ask(client, headers, "What should I do about the soil?")
    assert body["intent"] == "soil"
    assert "soil health" in body["message"].lower()
    titles = {s["title"] for s in body["sections"]}
    assert "Soil health" in titles
    assert "Recommended care" in titles


async def test_recovery_intent_reports_status(client, db):
    await _seed()
    headers = await _register(client, "+919310000012")
    user_id = await _user_id(db, "+919310000012")
    crop_id = await _crop_id("tomato")
    disease_id = await _disease_id("tomato", "Early Blight")
    await _make_scan(user_id, crop_id=crop_id, disease_id=disease_id)

    body = await _ask(client, headers, "How is my crop recovery going?")
    assert body["intent"] == "recovery"
    assert "recovered" in body["message"]
    assert body["sections"][0]["title"] == "Recovery"


async def test_calendar_intent_reads_today_tasks(client):
    await _seed()
    headers = await _register(client, "+919310000013")

    # No schedules yet → a "caught up" reply, not an error.
    before = await _ask(client, headers, "Read today's farming tasks.")
    assert before["intent"] == "calendar"
    assert "caught up" in before["message"]

    # Schedule a crop planted today → watering + basal fertilizer due today.
    crop_id = await _crop_id("tomato")
    resp = await client.post(f"/api/v1/calendar/crops/{crop_id}/schedule", json={}, headers=headers)
    assert resp.status_code == 201, resp.text

    after = await _ask(client, headers, "Read today's farming tasks.")
    assert after["intent"] == "calendar"
    assert "due today" in after["message"]
    assert any("Water the Tomato" in s["body"] for s in after["sections"])


async def test_hindi_treatment_reply_is_localized(client, db):
    await _seed()
    headers = await _register(client, "+919310000014")
    user_id = await _user_id(db, "+919310000014")
    crop_id = await _crop_id("tomato")
    disease_id = await _disease_id("tomato", "Early Blight")
    await _make_scan(user_id, crop_id=crop_id, disease_id=disease_id)

    body = await _ask(client, headers, "इस रोग का इलाज कैसे करूँ?")
    assert body["intent"] == "treatment"
    assert body["lang"] == "hi"
    assert any(s["title"] == "घरेलू उपाय" for s in body["sections"])
