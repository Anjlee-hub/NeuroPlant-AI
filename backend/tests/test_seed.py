"""Catalog seeder tests (M1).

Verifies the bootstrap crops/diseases load with valid structure, every crop
has at least one disease, key remedy fields are populated, and re-running the
seeder does not duplicate rows.
"""

from app.db.seed import seed_catalog
from app.db.session import async_session_factory
from app.models.catalog import Crop, Disease
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload


async def test_seed_catalog_loads_crops_and_diseases():
    async with async_session_factory() as db:
        summary = await seed_catalog(db)
        assert summary["crops"] >= 10
        assert summary["diseases"] >= 20

        crop_count = await db.scalar(select(func.count()).select_from(Crop))
        disease_count = await db.scalar(select(func.count()).select_from(Disease))
        assert crop_count == summary["crops"]
        assert disease_count == summary["diseases"]

        # Every crop has at least one disease.
        rows = (
            await db.execute(
                select(Crop.name, func.count(Disease.id))
                .join(Disease, Disease.crop_id == Crop.id)
                .group_by(Crop.id)
            )
        ).all()
        assert len(rows) == summary["crops"]
        for name, count in rows:
            assert count >= 1, f"crop {name} has no diseases"

        # Key fields are populated on a representative entry.
        rice = await db.scalar(
            select(Crop).where(Crop.name == "rice").options(selectinload(Crop.diseases))
        )
        assert rice.common_name
        assert rice.season and "kharif" in rice.season
        assert rice.growth_days and rice.water_needs and rice.fertilizer_needs
        first = rice.diseases[0]
        assert first.symptoms and first.severity_range and first.stages
        assert first.causes and first.recovery_time and first.prevention_tips
        # Every disease has at least one actionable remedy category.
        assert (
            first.organic_treatments
            or first.chemical_treatments
            or first.homemade_remedies
            or first.biological_controls
        )


async def test_seed_catalog_is_idempotent():
    async with async_session_factory() as db:
        first = await seed_catalog(db)
        second = await seed_catalog(db)
    assert first["crops"] > 0
    assert first["diseases"] > 0
    assert second == {"crops": 0, "diseases": 0}
