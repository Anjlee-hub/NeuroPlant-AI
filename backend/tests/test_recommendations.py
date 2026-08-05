"""M3, Task 1 tests — treatment recommendation engine.

Covers the seeder (catalog build + idempotency), the read-only
``/recommendations`` endpoints (catalog metadata + per-disease plans), and the
``/scans/{id}/recommendations`` lookup (ownership guard, by-id then by-name
resolution, and the no-plan 404). Plans are data-driven: every assertion checks
the seeded content, never a hardcoded treatment string in a controller.
"""

import uuid

from app.db.seed import seed_catalog, seed_recommendations
from app.db.session import async_session_factory
from app.models.catalog import Crop, Disease
from app.models.recommendation import DiseaseRecommendation, RecommendationCatalog
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


async def _tomato_early_blight_id() -> int:
    async with async_session_factory() as db:
        crop = await db.scalar(select(Crop).where(Crop.name == "tomato"))
        assert crop is not None
        disease = await db.scalar(
            select(Disease).where(Disease.crop_id == crop.id, Disease.name == "Early Blight")
        )
        assert disease is not None
        return disease.id


async def _make_scan(user_id: int, disease_id: int | None, disease_name: str) -> int:
    """Persist a scan directly (bypasses inference) for deterministic tests."""
    async with async_session_factory() as db:
        scan = await ScanService(db).create(
            ScanCreate(
                client_scan_id=_uuid(9000 + user_id),
                user_id=user_id,
                image_path="/media/test.jpg",
                media_items=[],
                crop_id=None,
                part_type="leaf",
                disease_id=disease_id,
                disease_name=disease_name,
                confidence=0.92,
                severity="moderate",
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


async def test_seed_recommendations_builds_active_catalog():
    async with async_session_factory() as db:
        await seed_catalog(db)
        summary = await seed_recommendations(db)
        assert summary["plans"] == 26

        catalog = await db.scalar(
            select(RecommendationCatalog).where(RecommendationCatalog.is_active.is_(True))
        )
        assert catalog is not None
        assert catalog.version == "v1"
        assert catalog.is_active is True

        count = await db.scalar(select(func.count()).select_from(DiseaseRecommendation))
        assert count == 26

        # Every plan is complete across the twelve guidance categories.
        plans = (await db.scalars(select(DiseaseRecommendation))).all()
        for plan in plans:
            assert plan.overview and plan.spread_mechanism and plan.severity
            assert plan.watering and plan.sunlight and plan.temperature and plan.humidity
            assert plan.fertilizer and plan.isolation and plan.recovery_timeline
            assert plan.symptoms and plan.monitoring_advice
            assert plan.homemade_remedies or plan.organic_remedies or plan.chemical_recommendations


async def test_seed_recommendations_is_idempotent():
    async with async_session_factory() as db:
        await seed_catalog(db)
        await seed_recommendations(db)
        again = await seed_recommendations(db)
        assert again["plans"] == 0
        count = await db.scalar(select(func.count()).select_from(DiseaseRecommendation))
        assert count == 26


async def test_tomato_and_potato_late_blight_get_distinct_plans():
    """Same disease name across crops must not share a plan."""
    async with async_session_factory() as db:
        await seed_catalog(db)
        await seed_recommendations(db)
        catalog = await db.scalar(
            select(RecommendationCatalog).where(RecommendationCatalog.is_active.is_(True))
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
            select(DiseaseRecommendation).where(
                DiseaseRecommendation.catalog_id == catalog.id,
                DiseaseRecommendation.disease_id == tomato_d.id,
            )
        )
        p_plan = await db.scalar(
            select(DiseaseRecommendation).where(
                DiseaseRecommendation.catalog_id == catalog.id,
                DiseaseRecommendation.disease_id == potato_d.id,
            )
        )
        assert t_plan is not None and p_plan is not None
        assert t_plan.overview != p_plan.overview
        # Curated content won the merge; symptoms fall back to the Disease row.
        assert t_plan.overview.startswith("A fast-spreading")


async def test_new_catalog_version_deactivates_previous():
    """Bumping RECOMMENDATION_VERSION must atomically swap the active catalog."""
    from unittest.mock import patch

    async with async_session_factory() as db:
        await seed_catalog(db)
        await seed_recommendations(db)
        first_catalog_id = await db.scalar(
            select(RecommendationCatalog.id).where(RecommendationCatalog.is_active.is_(True))
        )

        # seed.py binds RECOMMENDATION_VERSION at import time — patch that name.
        with patch("app.db.seed.RECOMMENDATION_VERSION", "v2"):
            summary = await seed_recommendations(db)
        # Every catalog disease is re-planted under the new version.
        assert summary["plans"] == 26

        active = await db.scalar(
            select(RecommendationCatalog).where(RecommendationCatalog.is_active.is_(True))
        )
        assert active.version == "v2"
        assert active.id != first_catalog_id
        v1_active = await db.scalar(
            select(func.count())
            .select_from(RecommendationCatalog)
            .where(
                RecommendationCatalog.version == "v1",
                RecommendationCatalog.is_active.is_(True),
            )
        )
        assert v1_active == 0


# ── /recommendations endpoints ───────────────────────────────────────────


async def test_recommendations_require_auth(client):
    assert (await client.get("/api/v1/recommendations/catalog")).status_code == 401
    assert (await client.get("/api/v1/recommendations/diseases/1")).status_code == 401


async def test_catalog_unavailable_returns_503(client):
    """No active catalog (seeder never ran) → 503, not a crash."""
    await _seed_all()
    # Sabotage: deactivate the catalog to simulate an unseeded deployment.
    async with async_session_factory() as db:
        from sqlalchemy import update

        await db.execute(update(RecommendationCatalog).values(is_active=False))
        await db.commit()

    headers = await _register(client, "+919000000001")
    resp = await client.get("/api/v1/recommendations/catalog", headers=headers)
    assert resp.status_code == 503
    assert "seeded" in resp.json()["error"]["message"].lower()


async def test_catalog_metadata_endpoint(client):
    await _seed_all()
    headers = await _register(client, "+919000000002")
    resp = await client.get("/api/v1/recommendations/catalog", headers=headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["version"] == "v1"
    assert body["is_active"] is True
    assert body["disease_count"] == 26
    assert body["description"]


async def test_disease_recommendation_endpoint(client):
    await _seed_all()
    disease_id = await _tomato_early_blight_id()
    headers = await _register(client, "+919000000003")
    resp = await client.get(f"/api/v1/recommendations/diseases/{disease_id}", headers=headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["catalog_version"] == "v1"
    assert body["disease"]["name"] == "Early Blight"
    assert body["disease"]["crop_name"] == "Tomato"
    assert body["overview"] and body["spread_mechanism"] and body["severity"]
    assert body["symptoms"] and body["monitoring_advice"]
    # All three treatment categories present, structured (not prose).
    assert body["homemade_remedies"]
    assert body["organic_remedies"]
    assert body["chemical_recommendations"]
    first_chem = body["chemical_recommendations"][0]
    assert {"category", "product", "dosage", "application_interval", "safety_precautions"} <= set(
        first_chem
    )
    assert first_chem["safety_precautions"]
    assert body["fertilizer"] and body["watering"] and body["sunlight"]
    assert body["temperature"] and body["humidity"]
    assert body["isolation"] and body["recovery_timeline"]


async def test_disease_recommendation_404_for_unknown(client):
    await _seed_all()
    headers = await _register(client, "+919000000004")
    resp = await client.get("/api/v1/recommendations/diseases/999999", headers=headers)
    assert resp.status_code == 404
    assert "no treatment plan" in resp.json()["error"]["message"].lower()


# ── /scans/{id}/recommendations ──────────────────────────────────────────


async def test_scan_recommendations_happy_path(client, db):
    await _seed_all()
    headers = await _register(client, "+919000000005")
    user_id = await _user_id(client, db, "+919000000005")
    disease_id = await _tomato_early_blight_id()
    scan_id = await _make_scan(user_id, disease_id, "Early Blight")

    resp = await client.get(f"/api/v1/scans/{scan_id}/recommendations", headers=headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["disease"]["id"] == disease_id
    assert body["disease"]["name"] == "Early Blight"
    assert body["catalog_version"] == "v1"
    assert body["overview"] and body["homemade_remedies"] and body["chemical_recommendations"]


async def test_scan_recommendations_resolves_by_name_when_no_disease_id(client, db):
    """A scan with a null disease_id still gets a plan when the name matches."""
    await _seed_all()
    headers = await _register(client, "+919000000006")
    user_id = await _user_id(client, db, "+919000000006")
    scan_id = await _make_scan(user_id, None, "Early Blight")

    resp = await client.get(f"/api/v1/scans/{scan_id}/recommendations", headers=headers)
    assert resp.status_code == 200, resp.text
    assert resp.json()["disease"]["name"] == "Early Blight"


async def test_scan_recommendations_404_when_no_plan(client, db):
    await _seed_all()
    headers = await _register(client, "+919000000007")
    user_id = await _user_id(client, db, "+919000000007")
    scan_id = await _make_scan(user_id, None, "Mystery Disease")

    resp = await client.get(f"/api/v1/scans/{scan_id}/recommendations", headers=headers)
    assert resp.status_code == 404
    assert "no treatment plan" in resp.json()["error"]["message"].lower()


async def test_scan_recommendations_404_unknown_or_other_users_scan(client, db):
    await _seed_all()
    headers = await _register(client, "+919000000008")
    resp = await client.get("/api/v1/scans/999999/recommendations", headers=headers)
    assert resp.status_code == 404
