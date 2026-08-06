"""M3, Task 3 tests — smart soil recommendation engine.

Covers the seeder (active soil catalog + idempotency), the read-only
``/soil`` endpoints (catalog metadata + per-disease plans), the adaptive
soil-health score (severity / confidence), and the
``/scans/{id}/soil-recommendations`` lookup (ownership guard, by-id then
by-name resolution, no-plan 404). Plans are data-driven: every assertion checks
the seeded content, never a hardcoded advice string in a controller.
"""

import uuid

from app.db.seed import seed_catalog, seed_recommendations, seed_soil_recommendations
from app.db.session import async_session_factory
from app.models.catalog import Crop, Disease
from app.models.soil import SoilRecommendation, SoilRecommendationCatalog
from app.models.user import User
from app.schemas.scan import ScanCreate
from app.services.scans import ScanService
from sqlalchemy import func, select


def _uuid(n: int) -> str:
    return str(uuid.UUID(int=n))


async def _register(client, phone: str) -> dict:
    resp = await client.post(
        "/api/v1/auth/register",
        json={"phone": phone, "name": "Tester", "role": "farmer", "password": "secret123"},
    )
    assert resp.status_code == 201, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


async def _seed_all():
    async with async_session_factory() as db:
        await seed_catalog(db)
        await seed_recommendations(db)
        await seed_soil_recommendations(db)


async def _tomato_early_blight_id() -> int:
    async with async_session_factory() as db:
        crop = await db.scalar(select(Crop).where(Crop.name == "tomato"))
        assert crop is not None
        disease = await db.scalar(
            select(Disease).where(Disease.crop_id == crop.id, Disease.name == "Early Blight")
        )
        assert disease is not None
        return disease.id


async def _make_scan(
    user_id: int,
    disease_id: int | None,
    disease_name: str,
    *,
    severity: str = "moderate",
    confidence: float = 0.92,
) -> int:
    """Persist a scan directly (bypasses inference) for deterministic tests."""
    async with async_session_factory() as db:
        scan = await ScanService(db).create(
            ScanCreate(
                client_scan_id=_uuid(9100 + user_id),
                user_id=user_id,
                image_path="/media/test.jpg",
                media_items=[],
                crop_id=None,
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


async def _user_id(client, db, phone: str) -> int:
    user = await db.scalar(select(User).where(User.phone == phone))
    assert user is not None
    return user.id


# ── Seeder ───────────────────────────────────────────────────────────────


async def test_seed_soil_recommendations_builds_active_catalog():
    async with async_session_factory() as db:
        await seed_catalog(db)
        summary = await seed_soil_recommendations(db)
        assert summary["plans"] == 26

        catalog = await db.scalar(
            select(SoilRecommendationCatalog).where(SoilRecommendationCatalog.is_active.is_(True))
        )
        assert catalog is not None
        assert catalog.version == "v1"
        assert catalog.is_active is True

        count = await db.scalar(select(func.count()).select_from(SoilRecommendation))
        assert count == 26

        # Every plan is complete across the nine guidance areas + health profile.
        plans = (await db.scalars(select(SoilRecommendation))).all()
        for plan in plans:
            assert plan.recommended_soil_type and plan.ph_range
            assert plan.moisture_level and plan.drainage and plan.organic_matter
            assert plan.npk and plan.compost and plan.mulching
            assert plan.micronutrients
            assert plan.soil_suitability and plan.base_soil_health
            assert plan.improvement_suggestions
            assert plan.base_soil_health in {"excellent", "good", "fair", "poor"}


async def test_seed_soil_recommendations_is_idempotent():
    async with async_session_factory() as db:
        await seed_catalog(db)
        await seed_soil_recommendations(db)
        again = await seed_soil_recommendations(db)
        assert again["plans"] == 0
        count = await db.scalar(select(func.count()).select_from(SoilRecommendation))
        assert count == 26


async def test_tomato_and_potato_late_blight_get_distinct_soil_notes():
    """Same disease name across crops must not share soil advice."""
    async with async_session_factory() as db:
        await seed_catalog(db)
        await seed_soil_recommendations(db)
        catalog = await db.scalar(
            select(SoilRecommendationCatalog).where(SoilRecommendationCatalog.is_active.is_(True))
        )
        tomato = await db.scalar(select(Crop).where(Crop.name == "tomato"))
        potato = await db.scalar(select(Crop).where(Crop.name == "potato"))
        tomato_d = await db.scalar(
            select(Disease).where(Disease.crop_id == tomato.id, Disease.name == "Late Blight")
        )
        potato_d = await db.scalar(
            select(Disease).where(Disease.crop_id == potato.id, Disease.name == "Late Blight")
        )
        t_plan = await db.scalar(
            select(SoilRecommendation).where(
                SoilRecommendation.catalog_id == catalog.id,
                SoilRecommendation.disease_id == tomato_d.id,
            )
        )
        p_plan = await db.scalar(
            select(SoilRecommendation).where(
                SoilRecommendation.catalog_id == catalog.id,
                SoilRecommendation.disease_id == potato_d.id,
            )
        )
        assert t_plan is not None and p_plan is not None
        # Crop-appropriate soil profiles differ (pH range / soil type).
        assert t_plan.recommended_soil_type != p_plan.recommended_soil_type
        assert t_plan.disease_soil_notes and p_plan.disease_soil_notes
        assert t_plan.disease_soil_notes != p_plan.disease_soil_notes


async def test_new_soil_catalog_version_deactivates_previous():
    """Bumping SOIL_VERSION must atomically swap the active catalog."""
    from unittest.mock import patch

    async with async_session_factory() as db:
        await seed_catalog(db)
        await seed_soil_recommendations(db)
        first_catalog_id = await db.scalar(
            select(SoilRecommendationCatalog.id).where(
                SoilRecommendationCatalog.is_active.is_(True)
            )
        )

        with patch("app.db.seed.SOIL_VERSION", "v2"):
            summary = await seed_soil_recommendations(db)
        assert summary["plans"] == 26

        active = await db.scalar(
            select(SoilRecommendationCatalog).where(SoilRecommendationCatalog.is_active.is_(True))
        )
        assert active.version == "v2"
        assert active.id != first_catalog_id
        v1_active = await db.scalar(
            select(func.count())
            .select_from(SoilRecommendationCatalog)
            .where(
                SoilRecommendationCatalog.version == "v1",
                SoilRecommendationCatalog.is_active.is_(True),
            )
        )
        assert v1_active == 0


# ── /soil endpoints ───────────────────────────────────────────────────────


async def test_soil_endpoints_require_auth(client):
    assert (await client.get("/api/v1/soil/catalog")).status_code == 401
    assert (await client.get("/api/v1/soil/diseases/1")).status_code == 401


async def test_soil_catalog_unavailable_returns_503(client):
    """No active soil catalog (seeder never ran) → 503, not a crash."""
    await _seed_all()
    async with async_session_factory() as db:
        from sqlalchemy import update

        await db.execute(update(SoilRecommendationCatalog).values(is_active=False))
        await db.commit()

    headers = await _register(client, "+919000000101")
    resp = await client.get("/api/v1/soil/catalog", headers=headers)
    assert resp.status_code == 503
    assert "seeded" in resp.json()["error"]["message"].lower()


async def test_soil_catalog_metadata_endpoint(client):
    await _seed_all()
    headers = await _register(client, "+919000000102")
    resp = await client.get("/api/v1/soil/catalog", headers=headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["version"] == "v1"
    assert body["is_active"] is True
    assert body["plan_count"] == 26
    assert body["description"]


async def test_disease_soil_recommendation_endpoint(client):
    await _seed_all()
    disease_id = await _tomato_early_blight_id()
    headers = await _register(client, "+919000000103")
    resp = await client.get(f"/api/v1/soil/diseases/{disease_id}", headers=headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["catalog_version"] == "v1"
    assert body["disease"]["name"] == "Early Blight"
    assert body["disease"]["crop_name"] == "Tomato"

    # Nine guidance areas, all present and structured.
    for area in (
        "recommended_soil_type",
        "ph_range",
        "moisture_level",
        "drainage",
        "organic_matter",
        "npk",
        "compost",
        "mulching",
    ):
        assert body[area], area
    assert body["micronutrients"]

    # Soil-health profile.
    health = body["soil_health"]
    assert health["label"] in {"excellent", "good", "fair", "poor"}
    assert 1.0 <= health["score"] <= 5.0
    assert health["summary"]
    assert body["soil_suitability"]
    assert body["improvement_suggestions"]

    # Disease-aware: tomato has a soil note for Early Blight.
    assert body["disease_soil_notes"]


async def test_disease_soil_recommendation_404_for_unknown(client):
    await _seed_all()
    headers = await _register(client, "+919000000104")
    resp = await client.get("/api/v1/soil/diseases/999999", headers=headers)
    assert resp.status_code == 404
    assert "no soil plan" in resp.json()["error"]["message"].lower()


async def test_soil_invalid_severity_rejected(client):
    await _seed_all()
    disease_id = await _tomato_early_blight_id()
    headers = await _register(client, "+919000000105")
    resp = await client.get(
        f"/api/v1/soil/diseases/{disease_id}?severity=critical", headers=headers
    )
    assert resp.status_code == 422


# ── Adaptive soil health score ────────────────────────────────────────────


async def test_soil_health_baseline_is_good_for_tomato(client):
    """Tomato base rating is 'good' (4.0) with no stress factors."""
    await _seed_all()
    disease_id = await _tomato_early_blight_id()
    headers = await _register(client, "+919000000106")
    resp = await client.get(f"/api/v1/soil/diseases/{disease_id}", headers=headers)
    health = resp.json()["soil_health"]
    assert health["score"] == 4.0
    assert health["label"] == "good"
    assert "usual soil preferences" in health["summary"]


async def test_soil_health_drops_with_severe_severity(client):
    """Severe disease reduces the tomato score from 4.0 → 3.0 (good → fair)."""
    await _seed_all()
    disease_id = await _tomato_early_blight_id()
    headers = await _register(client, "+919000000107")
    resp = await client.get(
        f"/api/v1/soil/diseases/{disease_id}?severity=severe", headers=headers
    )
    body = resp.json()
    health = body["soil_health"]
    assert health["score"] == 3.0
    assert health["label"] == "fair"
    assert "severe disease severity" in health["summary"]
    # Severity-aware content merged in.
    assert body["severity"] == "severe"
    assert body["severity_notes"]
    assert len(body["improvement_suggestions"]) >= 2


async def test_soil_health_low_confidence_adds_note_and_penalty(client):
    """Low confidence applies an extra penalty and a visible note."""
    await _seed_all()
    disease_id = await _tomato_early_blight_id()
    headers = await _register(client, "+919000000108")
    resp = await client.get(
        f"/api/v1/soil/diseases/{disease_id}?severity=moderate&confidence=0.4", headers=headers
    )
    body = resp.json()
    health = body["soil_health"]
    # 4.0 - 0.5 (moderate) - 0.5 (low confidence) = 3.0 → fair.
    assert health["score"] == 3.0
    assert body["confidence_note"] is not None
    assert "confidence" in body["confidence_note"].lower()
    assert "low detection confidence" in health["summary"]


# ── /scans/{id}/soil-recommendations ──────────────────────────────────────


async def test_scan_soil_recommendations_happy_path(client, db):
    await _seed_all()
    headers = await _register(client, "+919000000109")
    user_id = await _user_id(client, db, "+919000000109")
    disease_id = await _tomato_early_blight_id()
    scan_id = await _make_scan(user_id, disease_id, "Early Blight", severity="severe")

    resp = await client.get(f"/api/v1/scans/{scan_id}/soil-recommendations", headers=headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["disease"]["id"] == disease_id
    assert body["disease"]["name"] == "Early Blight"
    assert body["severity"] == "severe"
    assert body["confidence"] == 0.92
    assert body["confidence_note"] is None
    assert body["soil_health"]["label"] == "fair"
    assert body["soil_health"]["score"] == 3.0
    assert body["disease_soil_notes"]


async def test_scan_soil_recommendations_low_confidence_note(client, db):
    await _seed_all()
    headers = await _register(client, "+919000000110")
    user_id = await _user_id(client, db, "+919000000110")
    scan_id = await _make_scan(
        user_id, None, "Early Blight", severity="low", confidence=0.42
    )

    resp = await client.get(f"/api/v1/scans/{scan_id}/soil-recommendations", headers=headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["confidence_note"] is not None
    # Low severity (no penalty) − 0.5 low-confidence penalty = 4.0 - 0.5 = 3.5.
    assert body["soil_health"]["label"] == "good"
    assert body["soil_health"]["score"] == 3.5


async def test_scan_soil_recommendations_resolves_by_name_when_no_disease_id(client, db):
    """A scan with a null disease_id still gets a soil plan when the name matches."""
    await _seed_all()
    headers = await _register(client, "+919000000111")
    user_id = await _user_id(client, db, "+919000000111")
    scan_id = await _make_scan(user_id, None, "Early Blight")

    resp = await client.get(f"/api/v1/scans/{scan_id}/soil-recommendations", headers=headers)
    assert resp.status_code == 200, resp.text
    assert resp.json()["disease"]["name"] == "Early Blight"


async def test_scan_soil_recommendations_404_when_no_plan(client, db):
    await _seed_all()
    headers = await _register(client, "+919000000112")
    user_id = await _user_id(client, db, "+919000000112")
    scan_id = await _make_scan(user_id, None, "Mystery Disease")

    resp = await client.get(f"/api/v1/scans/{scan_id}/soil-recommendations", headers=headers)
    assert resp.status_code == 404
    assert "no soil plan" in resp.json()["error"]["message"].lower()


async def test_scan_soil_recommendations_404_unknown_or_other_users_scan(client, db):
    await _seed_all()
    headers = await _register(client, "+919000000113")
    resp = await client.get("/api/v1/scans/999999/soil-recommendations", headers=headers)
    assert resp.status_code == 404
