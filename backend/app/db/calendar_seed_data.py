"""Curated crop-calendar catalog (M3, Task 5).

A growth-stage template for every crop in the M1 knowledge catalog
(``app.db.seed_data``), keyed by crop common name for idempotent seeding. Each
plan defines the recommended sowing window (1–12, wrapping the new year) and the
five stage durations in days — germination, vegetative, flowering, fruiting,
harvest — which sum to the crop's days-to-maturity. A planting date plus this
plan yields every stage's date range deterministically, and the service expands
the same plan into the reminder task list.

Planting windows follow the seeded seasons (e.g. rice is a single kharif crop →
a tight June–July window; onion spans rabi + kharif → June–December). Adding a
new crop = one ``CalendarPlanSeed`` entry; adding a new signal (weather / GPS /
soil test) extends the request context, not this schema.
"""

from __future__ import annotations

from dataclasses import dataclass

# Bump when the catalog content changes; the seeder activates a new version.
CALENDAR_VERSION = "v1"


@dataclass(frozen=True)
class CalendarPlanSeed:
    """Growth-stage template for one crop in the calendar catalog."""

    crop_name: str
    planting_start_month: int
    planting_end_month: int
    germination_days: int
    vegetative_days: int
    flowering_days: int
    fruiting_days: int
    harvest_days: int
    notes: str = ""

    @property
    def growth_days(self) -> int:
        """Total days-to-maturity (sum of the five stage durations)."""
        return (
            self.germination_days
            + self.vegetative_days
            + self.flowering_days
            + self.fruiting_days
            + self.harvest_days
        )


CALENDAR_PLANS: dict[str, CalendarPlanSeed] = {
    # ══ Tomato (kharif / rabi / zaid → near year-round) ═══════════════════
    "Tomato": CalendarPlanSeed(
        crop_name="Tomato",
        planting_start_month=3,
        planting_end_month=11,
        germination_days=8,
        vegetative_days=22,
        flowering_days=15,
        fruiting_days=22,
        harvest_days=8,
        notes="Sow in well-drained sandy loam; stake and prune for airflow.",
    ),
    # ══ Potato (rabi / zaid) ═════════════════════════════════════════════
    "Potato": CalendarPlanSeed(
        crop_name="Potato",
        planting_start_month=10,
        planting_end_month=3,  # wraps the new year
        germination_days=12,
        vegetative_days=25,
        flowering_days=15,
        fruiting_days=25,
        harvest_days=13,
        notes="Use certified disease-free seed tubers; hilling aids tuber set.",
    ),
    # ══ Paddy / Rice (kharif) ════════════════════════════════════════════
    "Paddy / Rice": CalendarPlanSeed(
        crop_name="Paddy / Rice",
        planting_start_month=6,
        planting_end_month=7,
        germination_days=10,
        vegetative_days=35,
        flowering_days=20,
        fruiting_days=35,
        harvest_days=20,
        notes="Nursery sowing ahead of transplanting; keep a thin water layer.",
    ),
    # ══ Wheat (rabi) ═════════════════════════════════════════════════════
    "Wheat": CalendarPlanSeed(
        crop_name="Wheat",
        planting_start_month=10,
        planting_end_month=12,
        germination_days=8,
        vegetative_days=30,
        flowering_days=20,
        fruiting_days=30,
        harvest_days=22,
        notes="Timely sowing plus irrigation at crown-root and grain-fill stages.",
    ),
    # ══ Maize / Corn (kharif + rabi) ═════════════════════════════════════
    "Maize / Corn": CalendarPlanSeed(
        crop_name="Maize / Corn",
        planting_start_month=6,
        planting_end_month=11,
        germination_days=8,
        vegetative_days=25,
        flowering_days=15,
        fruiting_days=30,
        harvest_days=17,
        notes="High-yield hybrids need balanced nitrogen at knee-high and tassel.",
    ),
    # ══ Cotton (kharif) ══════════════════════════════════════════════════
    "Cotton": CalendarPlanSeed(
        crop_name="Cotton",
        planting_start_month=5,
        planting_end_month=6,
        germination_days=10,
        vegetative_days=40,
        flowering_days=30,
        fruiting_days=55,
        harvest_days=25,
        notes="Long-duration kharif crop; monitor bollworms through fruiting.",
    ),
    # ══ Chickpea / Chana (rabi) ══════════════════════════════════════════
    "Chickpea / Chana": CalendarPlanSeed(
        crop_name="Chickpea / Chana",
        planting_start_month=10,
        planting_end_month=11,
        germination_days=10,
        vegetative_days=30,
        flowering_days=20,
        fruiting_days=30,
        harvest_days=10,
        notes="Deep, moisture-retentive soil; avoid excess irrigation at flowering.",
    ),
    # ══ Onion (rabi + kharif) ════════════════════════════════════════════
    "Onion": CalendarPlanSeed(
        crop_name="Onion",
        planting_start_month=6,
        planting_end_month=12,
        germination_days=12,
        vegetative_days=30,
        flowering_days=18,
        fruiting_days=25,
        harvest_days=15,
        notes="Raised beds for bulb quality; stop watering as tops fall over.",
    ),
    # ══ Chilli / Chilli pepper (kharif + rabi) ════════════════════════════
    "Chilli / Chilli pepper": CalendarPlanSeed(
        crop_name="Chilli / Chilli pepper",
        planting_start_month=6,
        planting_end_month=11,
        germination_days=10,
        vegetative_days=25,
        flowering_days=15,
        fruiting_days=30,
        harvest_days=10,
        notes="Stake plants; mulch to keep soil splash off the leaves.",
    ),
    # ══ Brinjal / Eggplant (kharif + rabi) ════════════════════════════════
    "Brinjal / Eggplant": CalendarPlanSeed(
        crop_name="Brinjal / Eggplant",
        planting_start_month=6,
        planting_end_month=11,
        germination_days=10,
        vegetative_days=25,
        flowering_days=15,
        fruiting_days=30,
        harvest_days=15,
        notes="Long-pick duration; prune lower leaves for airflow and fruit grade.",
    ),
    # ══ Soybean (kharif) ═════════════════════════════════════════════════
    "Soybean": CalendarPlanSeed(
        crop_name="Soybean",
        planting_start_month=6,
        planting_end_month=7,
        germination_days=8,
        vegetative_days=30,
        flowering_days=15,
        fruiting_days=30,
        harvest_days=17,
        notes="Inoculate seed with rhizobium; avoid waterlogging at pod-fill.",
    ),
    # ══ Groundnut / Peanut (kharif + rabi) ════════════════════════════════
    "Groundnut / Peanut": CalendarPlanSeed(
        crop_name="Groundnut / Peanut",
        planting_start_month=6,
        planting_end_month=11,
        germination_days=10,
        vegetative_days=30,
        flowering_days=15,
        fruiting_days=35,
        harvest_days=20,
        notes="Light, well-drained soil; earthing-up helps pod penetration.",
    ),
}
