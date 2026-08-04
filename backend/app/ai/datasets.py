"""Dataset loaders for the AI layer.

A loader turns source data (today: the seeded diseases catalog) into the
label/class map a classifier trains or serves against. Catalog objects are
versioned so every model artifact can be traced to the label space it was
built on (docs/08-ai-pipeline.md).
"""

from dataclasses import dataclass, field
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.catalog import Disease

# Bump when the label space changes (new crops/diseases, re-labeling).
DATASET_VERSION = "v1"


@dataclass(frozen=True)
class DiseaseCatalog:
    """The label space the disease classifier trains/serves against."""

    version: str
    label_map: dict[str, int]  # disease name → class index
    class_count: int
    disease_ids: dict[str, int] = field(default_factory=dict)  # name → disease.id
    disease_crops: dict[str, int] = field(default_factory=dict)  # name → crop.id


class DatasetLoader(Protocol):
    def load(self) -> DiseaseCatalog: ...


def build_label_map(diseases: list[Disease]) -> DiseaseCatalog:
    """Build a deterministic class index over catalog diseases (first-seen order)."""
    label_map: dict[str, int] = {}
    disease_ids: dict[str, int] = {}
    disease_crops: dict[str, int] = {}
    for disease in diseases:
        if disease.name not in label_map:
            # First-seen order keeps indices dense (0..n-1) even with dupes.
            label_map[disease.name] = len(label_map)
        disease_ids[disease.name] = disease.id  # last row's id wins for lookup
        disease_crops[disease.name] = disease.crop_id  # last row's crop wins
    return DiseaseCatalog(
        version=DATASET_VERSION,
        label_map=label_map,
        class_count=len(label_map),
        disease_ids=disease_ids,
        disease_crops=disease_crops,
    )


async def load_catalog(db: AsyncSession) -> DiseaseCatalog:
    """Load the disease label space from the seeded catalog."""
    rows = (await db.execute(select(Disease).order_by(Disease.id))).scalars().all()
    return build_label_map(list(rows))
