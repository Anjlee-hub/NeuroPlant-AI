"""Catalog seeder (M1).

Loads the bootstrap crops + diseases from ``seed_data`` into the database.
Idempotent: an existing crop (matched by name) is skipped, so the script can be
re-run after schema changes without duplicating rows.

Usage:
    python -m app.db.seed
"""

import asyncio

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.db.seed_data import CROPS
from app.db.session import async_session_factory
from app.models.catalog import Crop, Disease

logger = get_logger("db.seed")


async def seed_catalog(db: AsyncSession) -> dict[str, int]:
    """Insert any missing crops/diseases. Returns ``{"crops": n, "diseases": n}``."""
    added_crops = 0
    added_diseases = 0
    for crop_seed in CROPS:
        existing = await db.scalar(select(Crop).where(Crop.name == crop_seed.name))
        if existing is not None:
            logger.info("crop_skipped", name=crop_seed.name)
            continue

        crop = Crop(
            name=crop_seed.name,
            common_name=crop_seed.common_name,
            family=crop_seed.family,
            season=crop_seed.season,
            growth_days=crop_seed.growth_days,
            water_needs=crop_seed.water_needs,
            fertilizer_needs=crop_seed.fertilizer_needs,
            image_url=crop_seed.image_url,
        )
        db.add(crop)
        await db.flush()
        added_crops += 1

        for d in crop_seed.diseases:
            db.add(
                Disease(
                    crop_id=crop.id,
                    name=d.name,
                    pathogen_type=d.pathogen_type,
                    symptoms=d.symptoms,
                    severity_range=d.severity_range,
                    stages=d.stages,
                    causes=d.causes,
                    recovery_time=d.recovery_time,
                    prevention_tips=d.prevention_tips,
                    organic_treatments=d.organic_treatments,
                    chemical_treatments=d.chemical_treatments,
                    homemade_remedies=d.homemade_remedies,
                    biological_controls=d.biological_controls,
                )
            )
            added_diseases += 1
        logger.info(
            "crop_seeded",
            name=crop_seed.name,
            diseases=len(crop_seed.diseases),
        )

    await db.commit()
    logger.info("seed_complete", crops_added=added_crops, diseases_added=added_diseases)
    return {"crops": added_crops, "diseases": added_diseases}


async def _run() -> None:
    async with async_session_factory() as db:
        summary = await seed_catalog(db)
    print(f"Seeded: {summary['crops']} crops, {summary['diseases']} diseases")


if __name__ == "__main__":
    asyncio.run(_run())
