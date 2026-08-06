"""Catalog seeder (M1) + recommendation (M3 T1) + soil (M3 T3) + calendar (M3 T5) seeders.

Loads the bootstrap crops + diseases from ``seed_data`` into the database, then
builds the versioned treatment-recommendation catalog from
``recommendation_seed_data``, the soil-intelligence catalog from
``soil_seed_data``, and the crop-calendar catalog from ``calendar_seed_data``.
All are idempotent: an existing crop (matched by name) or a catalog row (matched
by version/disease/crop) is skipped, so the script can be re-run after schema
changes without duplicating rows.

Usage:
    python -m app.db.seed
"""

import asyncio

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.db.calendar_seed_data import CALENDAR_PLANS, CALENDAR_VERSION
from app.db.recommendation_seed_data import (
    RECOMMENDATION_VERSION,
    RECOMMENDATIONS,
    ChemicalSeed,
    OrganicSeed,
    RemedySeed,
)
from app.db.seed_data import CROPS
from app.db.session import async_session_factory
from app.db.soil_seed_data import SOIL_BY_CROP, SOIL_VERSION
from app.models.calendar import CropCalendarCatalog, CropCalendarPlan
from app.models.catalog import Crop, Disease
from app.models.recommendation import DiseaseRecommendation, RecommendationCatalog
from app.models.soil import SoilRecommendation, SoilRecommendationCatalog

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


# ── Recommendation catalog (M3, Task 1) ─────────────────────────────────


def _remedy_dict(seed: RemedySeed) -> dict:
    """RemedySeed -> HomemadeRemedyOut-shaped dict."""
    return {
        "title": seed.title,
        "category": seed.category,
        "ingredients": list(seed.ingredients),
        "instructions": seed.instructions,
        "frequency": seed.frequency,
    }


def _organic_dict(seed: OrganicSeed) -> dict:
    """OrganicSeed -> OrganicRemedyOut-shaped dict."""
    return {
        "title": seed.title,
        "category": seed.category,
        "application": seed.application,
        "frequency": seed.frequency,
    }


def _chemical_dict(seed: ChemicalSeed) -> dict:
    """ChemicalSeed -> ChemicalRecommendationOut-shaped dict."""
    return {
        "category": seed.category,
        "product": seed.product,
        "dosage": seed.dosage,
        "application_interval": seed.application_interval,
        "safety_precautions": list(seed.safety),
    }


def _fallback_plan(disease: Disease) -> dict:
    """Structured plan derived from an un-curated ``Disease`` row.

    Keeps every catalog disease self-contained: the flat M1 treatment lists are
    wrapped in the same structured shapes the engine returns, with conservative
    dose/interval placeholders. Curated seeds always override this — it only
    runs when a disease was added to the catalog but not yet to
    ``RECOMMENDATIONS``.
    """
    return {
        "homemade_remedies": [
            {
                "title": text,
                "category": "homemade-spray",
                "ingredients": [],
                "instructions": text,
                "frequency": "as directed",
            }
            for text in (disease.homemade_remedies or [])
        ],
        "organic_remedies": [
            {
                "title": text,
                "category": "bio-fungicide",
                "application": text,
                "frequency": "as directed",
            }
            for text in (
                list(disease.organic_treatments or []) + list(disease.biological_controls or [])
            )
        ],
        "chemical_recommendations": [
            {
                "category": "fungicide",
                "product": text,
                "dosage": "as per label",
                "application_interval": "as directed",
                "safety_precautions": list(ChemicalSeed.safety),
            }
            for text in (disease.chemical_treatments or [])
        ],
    }


async def seed_recommendations(db: AsyncSession) -> dict[str, int]:
    """Build the active treatment catalog.

    Exactly one ``RecommendationCatalog`` is active at a time; activating a new
    version deactivates the previous one (atomic from the API's point of view).
    Returns ``{"catalog": 1, "plans": n}`` (created-plan count).
    """
    # Ensure the catalog for the current version exists and is the only active one.
    catalog = await db.scalar(
        select(RecommendationCatalog).where(RecommendationCatalog.version == RECOMMENDATION_VERSION)
    )
    if catalog is None:
        catalog = RecommendationCatalog(
            version=RECOMMENDATION_VERSION,
            description="Curated treatment plans for every catalog disease.",
            is_active=True,
        )
        await db.execute(update(RecommendationCatalog).values(is_active=False))
        db.add(catalog)
        await db.flush()
    elif not catalog.is_active:
        await db.execute(update(RecommendationCatalog).values(is_active=False))
        catalog.is_active = True
        await db.flush()

    created = 0
    existing = {
        row.disease_id
        for row in await db.scalars(
            select(DiseaseRecommendation).where(DiseaseRecommendation.catalog_id == catalog.id)
        )
    }

    for crop_seed in CROPS:
        crop = await db.scalar(select(Crop).where(Crop.name == crop_seed.name))
        if crop is None:
            continue
        for disease_seed in crop_seed.diseases:
            disease = await db.scalar(
                select(Disease).where(
                    Disease.crop_id == crop.id,
                    Disease.name == disease_seed.name,
                )
            )
            if disease is None or disease.id in existing:
                continue

            plan = _fallback_plan(disease)
            curated = RECOMMENDATIONS.get((crop.common_name or crop.name, disease.name))
            if curated is not None:
                plan.update(
                    {
                        "overview": curated.overview,
                        "cause": curated.cause or disease.causes,
                        "symptoms": list(curated.symptoms) or list(disease.symptoms or []),
                        "severity": curated.severity,
                        "spread_mechanism": curated.spread_mechanism,
                        "homemade_remedies": [_remedy_dict(r) for r in curated.homemade],
                        "organic_remedies": [_organic_dict(o) for o in curated.organic],
                        "chemical_recommendations": [_chemical_dict(c) for c in curated.chemical],
                        "fertilizer": curated.fertilizer,
                        "watering": curated.watering,
                        "sunlight": curated.sunlight,
                        "temperature": curated.temperature,
                        "humidity": curated.humidity,
                        "prevention_tips": list(curated.prevention_tips)
                        or list(disease.prevention_tips or []),
                        "recovery_timeline": curated.recovery_timeline or disease.recovery_time,
                        "isolation": curated.isolation,
                        "monitoring_advice": list(curated.monitoring_advice),
                    }
                )

            db.add(
                DiseaseRecommendation(
                    catalog_id=catalog.id,
                    disease_id=disease.id,
                    overview=plan.get("overview"),
                    cause=plan.get("cause"),
                    symptoms=plan.get("symptoms"),
                    severity=plan.get("severity"),
                    spread_mechanism=plan.get("spread_mechanism"),
                    homemade_remedies=plan.get("homemade_remedies"),
                    organic_remedies=plan.get("organic_remedies"),
                    chemical_recommendations=plan.get("chemical_recommendations"),
                    fertilizer=plan.get("fertilizer"),
                    watering=plan.get("watering"),
                    sunlight=plan.get("sunlight"),
                    temperature=plan.get("temperature"),
                    humidity=plan.get("humidity"),
                    prevention_tips=plan.get("prevention_tips"),
                    recovery_timeline=plan.get("recovery_timeline"),
                    isolation=plan.get("isolation"),
                    monitoring_advice=plan.get("monitoring_advice"),
                )
            )
            created += 1

    await db.commit()
    logger.info(
        "recommendations_seeded",
        version=RECOMMENDATION_VERSION,
        catalog_id=catalog.id,
        plans=created,
    )
    return {"catalog": 1, "plans": created}


# ── Crop calendar catalog (M3, Task 5) ────────────────────────────────────


async def seed_crop_calendar(db: AsyncSession) -> dict[str, int]:
    """Build the active crop-calendar catalog.

    Mirrors ``seed_recommendations`` / ``seed_soil_recommendations``: exactly one
    ``CropCalendarCatalog`` is active at a time and a version bump deactivates
    the previous one. Each crop gets one ``CropCalendarPlan`` (planting window +
    stage durations) from ``CALENDAR_PLANS``; crops without a curated plan are
    skipped so seeding is never partial. Returns ``{"catalog": 1, "plans": n}``.
    """
    catalog = await db.scalar(
        select(CropCalendarCatalog).where(CropCalendarCatalog.version == CALENDAR_VERSION)
    )
    if catalog is None:
        catalog = CropCalendarCatalog(
            version=CALENDAR_VERSION,
            description="Curated growth-stage templates for every catalog crop.",
            is_active=True,
        )
        await db.execute(update(CropCalendarCatalog).values(is_active=False))
        db.add(catalog)
        await db.flush()
    elif not catalog.is_active:
        await db.execute(update(CropCalendarCatalog).values(is_active=False))
        catalog.is_active = True
        await db.flush()

    created = 0
    existing = {
        row.crop_id
        for row in await db.scalars(
            select(CropCalendarPlan).where(CropCalendarPlan.catalog_id == catalog.id)
        )
    }

    for crop in await db.scalars(select(Crop).order_by(Crop.id)):
        plan_seed = CALENDAR_PLANS.get(crop.common_name or crop.name)
        if plan_seed is None or crop.id in existing:
            continue
        db.add(
            CropCalendarPlan(
                catalog_id=catalog.id,
                crop_id=crop.id,
                planting_start_month=plan_seed.planting_start_month,
                planting_end_month=plan_seed.planting_end_month,
                germination_days=plan_seed.germination_days,
                vegetative_days=plan_seed.vegetative_days,
                flowering_days=plan_seed.flowering_days,
                fruiting_days=plan_seed.fruiting_days,
                harvest_days=plan_seed.harvest_days,
                notes=plan_seed.notes,
            )
        )
        created += 1

    await db.commit()
    logger.info(
        "crop_calendar_seeded",
        version=CALENDAR_VERSION,
        catalog_id=catalog.id,
        plans=created,
    )
    return {"catalog": 1, "plans": created}


# ── Soil catalog (M3, Task 3) ─────────────────────────────────────────────


async def seed_soil_recommendations(db: AsyncSession) -> dict[str, int]:
    """Build the active soil-intelligence catalog.

    Mirrors ``seed_recommendations``: exactly one ``SoilRecommendationCatalog``
    is active at a time and a version bump deactivates the previous one. Each
    catalog disease gets one ``SoilRecommendation`` row built from its crop's
    ``SOIL_BY_CROP`` profile, merged with the disease-specific soil note (if
    any) and the crop-level severity content. Returns ``{"catalog": 1,
    "plans": n}`` (created-plan count).
    """
    catalog = await db.scalar(
        select(SoilRecommendationCatalog).where(SoilRecommendationCatalog.version == SOIL_VERSION)
    )
    if catalog is None:
        catalog = SoilRecommendationCatalog(
            version=SOIL_VERSION,
            description="Curated soil guidance for every catalog crop and its diseases.",
            is_active=True,
        )
        await db.execute(update(SoilRecommendationCatalog).values(is_active=False))
        db.add(catalog)
        await db.flush()
    elif not catalog.is_active:
        await db.execute(update(SoilRecommendationCatalog).values(is_active=False))
        catalog.is_active = True
        await db.flush()

    created = 0
    existing = {
        row.disease_id
        for row in await db.scalars(
            select(SoilRecommendation).where(SoilRecommendation.catalog_id == catalog.id)
        )
    }

    for crop_seed in CROPS:
        crop = await db.scalar(select(Crop).where(Crop.name == crop_seed.name))
        if crop is None:
            continue
        profile = SOIL_BY_CROP.get(crop.common_name or crop.name)
        if profile is None:
            continue
        for disease_seed in crop_seed.diseases:
            disease = await db.scalar(
                select(Disease).where(
                    Disease.crop_id == crop.id,
                    Disease.name == disease_seed.name,
                )
            )
            if disease is None or disease.id in existing:
                continue

            db.add(
                SoilRecommendation(
                    catalog_id=catalog.id,
                    disease_id=disease.id,
                    recommended_soil_type=profile.recommended_soil_type,
                    ph_range=profile.ph_range,
                    moisture_level=profile.moisture_level,
                    drainage=profile.drainage,
                    organic_matter=profile.organic_matter,
                    npk=profile.npk,
                    micronutrients=list(profile.micronutrients),
                    compost=profile.compost,
                    mulching=profile.mulching,
                    soil_suitability=profile.soil_suitability,
                    base_soil_health=profile.base_soil_health,
                    improvement_suggestions=list(profile.improvement_suggestions),
                    disease_soil_notes=profile.disease_notes.get(disease.name),
                    severity_notes=dict(profile.severity_notes),
                    severity_suggestions=dict(profile.severity_suggestions),
                )
            )
            created += 1

    await db.commit()
    logger.info(
        "soil_recommendations_seeded",
        version=SOIL_VERSION,
        catalog_id=catalog.id,
        plans=created,
    )
    return {"catalog": 1, "plans": created}


async def _run() -> None:
    async with async_session_factory() as db:
        summary = await seed_catalog(db)
        recs = await seed_recommendations(db)
        soils = await seed_soil_recommendations(db)
        calendars = await seed_crop_calendar(db)
    print(
        f"Seeded: {summary['crops']} crops, {summary['diseases']} diseases; "
        f"{recs['plans']} recommendation plans; {soils['plans']} soil plans; "
        f"{calendars['plans']} calendar plans"
    )


if __name__ == "__main__":
    asyncio.run(_run())
