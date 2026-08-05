"""Curated treatment-recommendation catalog (M3, Task 1).

Structured, beginner-friendly treatment plans for every disease in the M1
knowledge catalog (``app.db.seed_data``), keyed by ``(crop common_name,
disease name)`` for idempotent seeding. Crops are disambiguated because the
catalog reuses disease names across crops (e.g. both tomato and potato have
``Late Blight``). Each plan covers the twelve guidance categories the engine
exposes:

    1. homemade remedies     5.  watering        9.  prevention tips
    2. organic remedies      6.  sunlight        10. recovery timeline
    3. chemical products     7.  temperature     11. isolation
    4. fertilizer            8.  humidity        12. monitoring advice

The seeder merges these curated plans with the existing ``Disease`` row fields
(symptoms / cause / prevention tips / recovery time) so every catalog disease
gets a complete, self-contained plan — curated fields win, catalog fields fill
the gaps. Adding a new disease = one dict entry here (or just a new catalog
disease, which the seeder covers by fallback) + a version bump.

Written for Indian field conditions: affordable kitchen ingredients, doses in
grams/litres used in Indian extension literature, and plain-language safety
steps. Advice is preventative/curative guidance, not a prescription.
"""

from __future__ import annotations

from dataclasses import dataclass

# Bump when the catalog content changes; the seeder activates a new version.
RECOMMENDATION_VERSION = "v1"

# Standard safety steps for any chemical spray (kept in one place).
_SPRAY_SAFETY: tuple[str, ...] = (
    "Wear gloves, a mask and full-sleeve clothes while mixing and spraying",
    "Spray in the early morning or late evening when wind is low",
    "Keep children, livestock and water sources away from sprayed plants for at least 24 hours",
    "Wash hands and equipment thoroughly after use",
)


@dataclass(frozen=True)
class RemedySeed:
    """A homemade remedy (kitchen ingredient / spray / traditional)."""

    title: str
    instructions: str
    frequency: str
    category: str = "homemade-spray"
    ingredients: tuple[str, ...] = ()


@dataclass(frozen=True)
class OrganicSeed:
    """An organic/biological remedy (neem oil, bio-fungicide, pesticide, nutrient)."""

    title: str
    application: str
    frequency: str
    category: str = "bio-fungicide"


@dataclass(frozen=True)
class ChemicalSeed:
    """A chemical product with dosage, interval and safety steps."""

    category: str
    product: str
    dosage: str
    application_interval: str
    safety: tuple[str, ...] = _SPRAY_SAFETY


@dataclass(frozen=True)
class RecommendationSeed:
    """One curated treatment plan for a disease (keyed by crop + disease name)."""

    disease_name: str
    crop_name: str
    overview: str
    spread_mechanism: str
    severity: str
    watering: str
    sunlight: str
    temperature: str
    humidity: str
    fertilizer: str
    isolation: str
    monitoring_advice: tuple[str, ...]
    recovery_timeline: str
    # Optional — when empty the seeder falls back to the Disease row fields.
    cause: str = ""
    symptoms: tuple[str, ...] = ()
    prevention_tips: tuple[str, ...] = ()
    homemade: tuple[RemedySeed, ...] = ()
    organic: tuple[OrganicSeed, ...] = ()
    chemical: tuple[ChemicalSeed, ...] = ()


# ── Compact constructors ────────────────────────────────────────────────


def _home(
    title: str,
    instructions: str,
    frequency: str,
    *,
    ingredients=(),
    category="homemade-spray",
):
    return RemedySeed(
        title=title,
        instructions=instructions,
        frequency=frequency,
        ingredients=tuple(ingredients),
        category=category,
    )


def _organic(title: str, application: str, frequency: str, *, category="bio-fungicide"):
    return OrganicSeed(title=title, application=application, frequency=frequency, category=category)


def _chem(category: str, product: str, dosage: str, interval: str):
    return ChemicalSeed(
        category=category, product=product, dosage=dosage, application_interval=interval
    )


RECOMMENDATIONS: dict[tuple[str, str], RecommendationSeed] = {
    # ══ Tomato ══════════════════════════════════════════════════════════
    ("Tomato", "Early Blight"): RecommendationSeed(
        disease_name="Early Blight",
        crop_name="Tomato",
        overview=(
            "A very common fungal disease that starts on the lower, older leaves and can "
            "defoliate the plant if left untreated."
        ),
        spread_mechanism=(
            "Spores travel on wind, rain splash and overhead irrigation water; the fungus "
            "survives in soil, plant debris and infected seed."
        ),
        severity="moderate",
        watering=(
            "Water at the base early in the morning; keep leaves dry and never use overhead "
            "sprinklers."
        ),
        sunlight="Full sun with good airflow — space plants and prune lower leaves.",
        temperature="Warm, humid weather (20-30 C) favours spread; avoid dense canopies.",
        humidity="High humidity and frequent dew spread it fastest; improve ventilation.",
        fertilizer="Balanced NPK; avoid excess nitrogen, add potassium to harden plants.",
        isolation=(
            "Remove infected lower leaves and rogue badly hit plants; do not compost "
            "diseased debris."
        ),
        monitoring_advice=(
            "Check older leaves weekly for dark concentric-ring spots",
            "After rain, scout for yellowing and die-back of lower foliage",
        ),
        recovery_timeline="2-3 weeks with treatment; plants recover fully if caught early",
        homemade=(
            _home(
                "Baking-soda spray",
                "Mix 1 tsp baking soda + 1 tsp oil in 1 L water; spray all leaf surfaces weekly.",
                "once a week",
                ingredients=("Baking soda 1 tsp", "Cooking oil 1 tsp", "Water 1 L"),
                category="kitchen-ingredients",
            ),
            _home(
                "Garlic-pepper tea",
                "Soak crushed garlic in 1 L water for 24 hours, strain and spray on leaves.",
                "every 10 days",
                ingredients=("Garlic 5-6 cloves", "Water 1 L"),
                category="traditional",
            ),
        ),
        organic=(
            _organic(
                "Copper oxychloride biofungicide",
                "Spray copper oxychloride 0.25% (2.5 g/L water) on leaves and stems.",
                "every 10-12 days",
                category="bio-fungicide",
            ),
            _organic(
                "Neem-based biofungicide",
                "Foliar spray of neem-based biofungicide at label dose.",
                "every 10 days",
                category="neem-oil",
            ),
        ),
        chemical=(
            _chem(
                "fungicide",
                "Mancozeb 75% WP",
                "2.5 g per litre of water",
                "at first sign, then every 14 days",
            ),
            _chem(
                "fungicide",
                "Chlorothalonil 75% WP",
                "2 g per litre of water",
                "every 10-14 days as a protectant",
            ),
        ),
    ),
    ("Tomato", "Late Blight"): RecommendationSeed(
        disease_name="Late Blight",
        crop_name="Tomato",
        overview=(
            "A fast-spreading, destructive disease that can wipe out a crop within days in "
            "cool, wet weather — act the moment symptoms appear."
        ),
        spread_mechanism=(
            "Spores spread rapidly by wind and rain splash; the pathogen survives on plant "
            "debris and volunteer tomato/potato plants."
        ),
        severity="severe",
        watering="Water at the base only, early morning; never wet the foliage.",
        sunlight="Maximise sun and airflow; avoid shaded, humid pockets in the field.",
        temperature="Cool (15-22 C) wet weather is the danger window — most severe after rains.",
        humidity="High humidity and wet leaves drive spread; keep foliage dry and ventilated.",
        fertilizer="Withhold nitrogen; apply potassium to strengthen plants against infection.",
        isolation=(
            "Remove and destroy infected plants immediately; keep a clear buffer from healthy rows."
        ),
        monitoring_advice=(
            "Scout daily after rain — check leaf undersides for white cottony growth",
            "Watch for water-soaked grey-green patches that enlarge quickly",
        ),
        recovery_timeline="1-2 weeks if caught early; the crop can be lost if weather stays wet",
        homemade=(
            _home(
                "Neem oil preventive spray",
                "Mix 5 ml neem oil + a drop of soap in 1 L water; spray all surfaces weekly.",
                "once a week",
                ingredients=("Neem oil 5 ml", "Water 1 L", "Soap a drop"),
                category="homemade-spray",
            ),
            _home(
                "Chamomile tea spray",
                "Steep chamomile in hot water, cool, strain and spray to suppress early spread.",
                "every 5-7 days",
                ingredients=("Chamomile flowers", "Water 1 L"),
                category="traditional",
            ),
        ),
        organic=(
            _organic(
                "Copper-based fungicide",
                "Spray copper-based fungicide 0.3% (3 g/L water) over the whole plant.",
                "every 7-10 days in wet weather",
                category="bio-fungicide",
            ),
            _organic(
                "Kelp/seaweed extract",
                "Foliar spray of kelp/seaweed extract to harden plant tissues.",
                "every 10-14 days",
                category="organic-nutrient",
            ),
        ),
        chemical=(
            _chem(
                "fungicide",
                "Metalaxyl + Mancozeb 68% WG",
                "2.5 g per litre of water",
                "at first symptoms, every 7-10 days",
            ),
            _chem(
                "fungicide",
                "Cymoxanil + Mancozeb",
                "1.5 g per litre of water",
                "every 7-10 days; alternate chemistries to avoid resistance",
            ),
        ),
    ),
    ("Tomato", "Tomato Leaf Curl"): RecommendationSeed(
        disease_name="Tomato Leaf Curl",
        crop_name="Tomato",
        overview=(
            "A virus disease spread by whitefly. There is no cure once infected — the plan "
            "is to control the vector and remove infected plants."
        ),
        spread_mechanism=(
            "Transmitted by whitefly (Bemisia tabaci) feeding; the virus persists in weeds "
            "and volunteer tomato plants."
        ),
        severity="high",
        watering="Keep plants well watered but avoid stress; do not over-fertilise.",
        sunlight="Grow under full sun; reflective plastic mulch repels whitefly.",
        temperature="Whitefly builds up in warm weather; monitor closely in summer.",
        humidity="Moderate humidity; avoid dense planting that shelters whitefly.",
        fertilizer="Avoid excess nitrogen which attracts whitefly to new growth.",
        isolation="Rogue and destroy infected plants promptly so the vector does not move on.",
        monitoring_advice=(
            "Check under young leaves weekly for whitefly adults and nymphs",
            "Watch for leaf curling and stunting of the top growth",
        ),
        recovery_timeline=(
            "No cure once infected; manage the vector and rogue plants to limit spread"
        ),
        organic=(
            _organic(
                "Neem oil whitefly spray",
                "Mix 5 ml neem oil in 1 L water; spray leaf undersides.",
                "every 7 days",
                category="neem-oil",
            ),
            _organic(
                "Botanical oil (karanj/nim)",
                "Spray botanical oil on leaf undersides to suppress whitefly.",
                "every 7-10 days",
                category="organic-pesticide",
            ),
        ),
        chemical=(
            _chem(
                "insecticide",
                "Imidacloprid 17.8% SL",
                "0.3 ml per litre of water",
                "on whitefly hotspots, every 10-14 days",
            ),
            _chem(
                "insecticide",
                "Diafenthiuron 50% WP",
                "1.2 g per litre of water",
                "as a rotational spray, every 10-14 days",
            ),
        ),
        prevention_tips=(
            "Use resistant varieties and raise seedlings under insect-proof net",
            "Set up yellow sticky traps (10-12 per hectare) for whitefly",
            "Destroy weed hosts and volunteer plants around the field",
        ),
    ),
    # ══ Potato ══════════════════════════════════════════════════════════
    ("Potato", "Late Blight"): RecommendationSeed(
        disease_name="Late Blight",
        crop_name="Potato",
        overview=(
            "The classic potato disease — under cool wet weather it can destroy a field in "
            "a week. Protect tubers as well as foliage."
        ),
        spread_mechanism=(
            "Airborne spores spread on wind and rain; infected seed tubers and discarded "
            "cull piles are the primary sources."
        ),
        severity="severe",
        watering="Avoid over-irrigation and waterlogging; irrigate early so foliage dries.",
        sunlight="Full sun; hill up soil to keep tubers covered.",
        temperature="Cool, humid weather (15-22 C) is the danger window.",
        humidity="High humidity with wet foliage drives the disease; improve airflow.",
        fertilizer="Balanced nutrition; avoid excess nitrogen late in the season.",
        isolation="Destroy cull piles and volunteer potatoes; keep buffer rows from healthy crop.",
        monitoring_advice=(
            "Scout after every rain for water-soaked lesions with pale green halos",
            "Check for white mildew rings on the underside of lesions",
        ),
        recovery_timeline="1-2 weeks with aggressive treatment if caught early",
        homemade=(
            _home(
                "Baking soda + oil spray",
                "Mix 1 tsp baking soda + 1 tsp oil in 1 L water; spray all foliage.",
                "once a week",
                ingredients=("Baking soda 1 tsp", "Cooking oil 1 tsp", "Water 1 L"),
                category="kitchen-ingredients",
            ),
        ),
        organic=(
            _organic(
                "Copper oxychloride",
                "Spray copper oxychloride 0.25% (2.5 g/L water) on all foliage.",
                "weekly in wet weather",
                category="bio-fungicide",
            ),
            _organic(
                "Neem oil 3%",
                "Foliar spray of 3% neem oil as a preventive.",
                "every 7-10 days",
                category="neem-oil",
            ),
        ),
        chemical=(
            _chem(
                "fungicide",
                "Metalaxyl + Mancozeb",
                "2.5 g per litre of water",
                "at first symptom, every 7-10 days",
            ),
            _chem(
                "fungicide",
                "Chlorothalonil 75% WP",
                "2 g per litre of water",
                "every 10-14 days, rotated with mancozeb",
            ),
        ),
        prevention_tips=(
            "Plant only certified disease-free seed tubers",
            "Hill up soil to protect tubers from spores",
            "Remove and destroy volunteer plants and cull piles",
        ),
    ),
    ("Potato", "Early Blight"): RecommendationSeed(
        disease_name="Early Blight",
        crop_name="Potato",
        overview=(
            "A common fungal disease of stressed or older potato plants; causes target-like "
            "leaf spots and a leathery tuber rot."
        ),
        spread_mechanism=(
            "Spores carried on soil, debris and wind; favoured by warm humid conditions and "
            "nutrition stress."
        ),
        severity="moderate",
        watering="Use furrow irrigation instead of sprinklers; water early in the day.",
        sunlight="Full sun; good airflow between rows.",
        temperature="Warm, humid weather favours it; avoid lush, stressed canopies.",
        humidity="Moderate humidity; keep foliage dry.",
        fertilizer="Maintain balanced nutrition; avoid excess nitrogen.",
        isolation="Rogue heavily infected plants; rotate away from solanaceous crops.",
        monitoring_advice=(
            "Inspect lower leaves for target-like spots with concentric rings",
            "Check tubers at harvest for dry, leathery rot",
        ),
        recovery_timeline="2-3 weeks with treatment",
        homemade=(
            _home(
                "Neem seed extract spray",
                "Soak neem seed in water overnight, strain and spray weekly.",
                "once a week",
                ingredients=("Neem seeds", "Water"),
                category="traditional",
            ),
        ),
        organic=(
            _organic(
                "Copper-based fungicide",
                "Spray copper-based fungicide 0.3% (3 g/L water).",
                "every 10 days",
                category="bio-fungicide",
            ),
        ),
        chemical=(
            _chem(
                "fungicide",
                "Mancozeb 75% WP",
                "2.5 g per litre of water",
                "every 14 days",
            ),
            _chem(
                "fungicide",
                "Azoxystrobin 23% SC",
                "1 ml per litre of water",
                "for late-season protection, every 14 days",
            ),
        ),
    ),
    # ══ Rice ════════════════════════════════════════════════════════════
    ("Paddy / Rice", "Rice Blast"): RecommendationSeed(
        disease_name="Rice Blast",
        crop_name="Paddy / Rice",
        overview=(
            "One of the most damaging rice diseases worldwide; it attacks leaves, stems and "
            "the neck, and can destroy the panicle."
        ),
        spread_mechanism=(
            "Airborne spores travel long distances; excess nitrogen, cool nights and dense "
            "planting make it worse."
        ),
        severity="high",
        watering="Maintain an even water depth; avoid deep flooding and water stress.",
        sunlight="Full sun; avoid excessive seedling density.",
        temperature="Cool nights (20-26 C) with high humidity favour the disease.",
        humidity="High humidity with dew on leaves drives infection.",
        fertilizer="Split nitrogen applications; do not over-dose nitrogen at tillering.",
        isolation="Remove heavily infected tillers; avoid late and dense sowing.",
        monitoring_advice=(
            "Scout for diamond-shaped lesions with grey centres on leaves",
            "Check the panicle neck for grey, breaking lesions at heading",
        ),
        recovery_timeline="2-3 weeks with treatment; early action protects the panicle",
        homemade=(
            _home(
                "Cow-dung + turmeric slurry",
                "Mix cow-dung slurry with a little turmeric paste; apply as a prophylactic "
                "at tillering.",
                "at tillering",
                ingredients=("Cow dung", "Turmeric powder", "Water"),
                category="traditional",
            ),
        ),
        organic=(
            _organic(
                "Neem cake soil application",
                "Broadcast neem cake at 200 kg per hectare in standing water.",
                "once at tillering",
                category="organic-nutrient",
            ),
            _organic(
                "Pseudomonas fluorescens 2%",
                "Spray Pseudomonas fluorescens 2% at tillering.",
                "at tillering",
                category="bio-fungicide",
            ),
        ),
        chemical=(
            _chem(
                "fungicide",
                "Tricyclazole 75% WP",
                "0.6 g per litre of water",
                "at first lesions, repeat after 10-12 days",
            ),
            _chem(
                "fungicide",
                "Isoprothiolane 40% EC",
                "1.5 ml per litre of water",
                "at boot-leaf stage",
            ),
        ),
    ),
    ("Paddy / Rice", "Bacterial Leaf Blight"): RecommendationSeed(
        disease_name="Bacterial Leaf Blight",
        crop_name="Paddy / Rice",
        overview=(
            "A bacterial disease of rice that yellows leaves from the tips and can cause "
            "heavy yield loss in the tillering and flowering stages."
        ),
        spread_mechanism=(
            "Spread by flood irrigation water, wind and rain injury; carried in infected "
            "seed and stubble."
        ),
        severity="high",
        watering="Avoid deep flooding during the vegetative stage; drain and air the field.",
        sunlight="Full sun; do not crowd plants.",
        temperature="Warm, windy weather with rain spreads it quickly.",
        humidity="High humidity with leaf wetness favours the bacterium.",
        fertilizer="Reduce nitrogen doses at peak tillering; keep nutrition balanced.",
        isolation="Rogue infected plants; drain water out of infected patches.",
        monitoring_advice=(
            "Watch for yellow lesions starting at leaf tips and spreading downward",
            "Check for milky bacterial ooze on leaves in wet weather",
        ),
        recovery_timeline="2-4 weeks with careful water and nitrogen management",
        chemical=(
            _chem(
                "bactericide",
                "Streptocycline + copper oxychloride",
                "0.2 g + 0.3% (3 g/L water) per litre",
                "at first sign, repeat after 15 days",
            ),
            _chem(
                "bactericide",
                "Copper fungicide",
                "as per label",
                "at first sign, repeat after 15 days",
            ),
        ),
    ),
    ("Paddy / Rice", "Sheath Blight"): RecommendationSeed(
        disease_name="Sheath Blight",
        crop_name="Paddy / Rice",
        overview=(
            "A fungal disease that blights the leaf sheaths near the waterline, common in "
            "dense, high-humidity crops."
        ),
        spread_mechanism=(
            "Dense canopies with high humidity; excess nitrogen and infected sclerotia in "
            "the soil spread it."
        ),
        severity="moderate",
        watering="Drain fields periodically at tillering; avoid continuous standing water.",
        sunlight="Reduce seedling density for more light and airflow.",
        temperature="Warm, humid weather (25-35 C) favours the fungus.",
        humidity="High humidity inside the canopy is the trigger — ventilate the crop.",
        fertilizer="Avoid excess nitrogen and dense sowing.",
        isolation="Remove and destroy heavily infected plants and debris.",
        monitoring_advice=(
            "Look for greenish-grey oval lesions on sheaths near the waterline",
            "Check for poor grain fill and chalky kernels late in the season",
        ),
        recovery_timeline="2-3 weeks with treatment",
        organic=(
            _organic(
                "Pseudomonas fluorescens 2%",
                "Spray Pseudomonas fluorescens 2% at sheath elongation.",
                "at sheath elongation",
                category="bio-fungicide",
            ),
        ),
        chemical=(
            _chem(
                "fungicide",
                "Validamycin 3% L",
                "2.5 ml per litre of water",
                "at disease onset, repeat after 10 days",
            ),
            _chem(
                "fungicide",
                "Hexaconazole 5% EC",
                "2 ml per litre of water",
                "at boot stage",
            ),
        ),
    ),
    # ══ Wheat ═══════════════════════════════════════════════════════════
    ("Wheat", "Leaf Rust"): RecommendationSeed(
        disease_name="Leaf Rust",
        crop_name="Wheat",
        overview=(
            "A wind-borne fungal rust of wheat that forms orange pustules on leaves and can "
            "shrink grain weight if it strikes early."
        ),
        spread_mechanism=(
            "Spores travel long distances on wind; the rust overwinters on volunteer wheat "
            "and grassy weeds."
        ),
        severity="moderate",
        watering="Irrigate at critical stages (tillering, stem elongation, heading); avoid stress.",
        sunlight="Full sun; avoid lush, shaded canopies.",
        temperature="Cool moist weather (15-25 C) favours rust development.",
        humidity="Morning dew on leaves aids infection; plant early to escape peak rust weather.",
        fertilizer="Avoid excess nitrogen that promotes lush growth.",
        isolation="Remove volunteer wheat and grassy weeds around the field.",
        monitoring_advice=(
            "Scout for small orange-brown pustules on leaves from tillering",
            "Check whether pustules burst and release orange powder",
        ),
        recovery_timeline="1-2 weeks with treatment if caught at first pustules",
        organic=(
            _organic(
                "Neem oil 1%",
                "Foliar spray of 1% neem oil at first pustules.",
                "every 7-10 days",
                category="neem-oil",
            ),
        ),
        chemical=(
            _chem(
                "fungicide",
                "Propiconazole 25% EC",
                "1 ml per litre of water",
                "at first rust, repeat after 15 days if needed",
            ),
            _chem(
                "fungicide",
                "Tebuconazole 25.9% EC",
                "1 ml per litre of water",
                "at first rust, repeat after 15 days if needed",
            ),
        ),
    ),
    ("Wheat", "Powdery Mildew"): RecommendationSeed(
        disease_name="Powdery Mildew",
        crop_name="Wheat",
        overview=(
            "A fungal disease that coats wheat leaves in white powder; it slows the plant "
            "and shrivels grain in dense, humid stands."
        ),
        spread_mechanism=(
            "Spores spread through the air within the crop; dense sowing, cool humid weather "
            "and high nitrogen favour it."
        ),
        severity="low",
        watering="Irrigate moderately; avoid overwatering that raises humidity.",
        sunlight="Reduce seeding rate for light and airflow.",
        temperature="Cool (15-25 C) humid weather favours it.",
        humidity="High humidity with poor airflow is the trigger.",
        fertilizer="Balanced nitrogen; avoid lush growth.",
        isolation="Avoid dense patches; rogue badly infected plants.",
        monitoring_advice=(
            "Check leaves and stems for white powdery growth",
            "Watch for yellowing and browning of covered leaves",
        ),
        recovery_timeline="1-2 weeks with treatment",
        homemade=(
            _home(
                "Milk spray",
                "Mix 1 part milk with 9 parts water; spray the crop.",
                "once a week",
                ingredients=("Milk 1 part", "Water 9 parts"),
                category="kitchen-ingredients",
            ),
        ),
        organic=(
            _organic(
                "Wettable sulphur 0.3%",
                "Dust sulphur or spray wettable sulphur 0.3% (3 g/L water).",
                "every 10-12 days",
                category="bio-fungicide",
            ),
        ),
        chemical=(
            _chem(
                "fungicide",
                "Tridemorph 80% EC",
                "0.75 ml per litre of water",
                "at first symptoms",
            ),
            _chem(
                "fungicide",
                "Propiconazole 25% EC",
                "1 ml per litre of water",
                "as an alternative",
            ),
        ),
    ),
    # ══ Maize ═══════════════════════════════════════════════════════════
    ("Maize / Corn", "Northern Corn Leaf Blight"): RecommendationSeed(
        disease_name="Northern Corn Leaf Blight",
        crop_name="Maize / Corn",
        overview=(
            "A fungal disease of maize that makes long grey-green lesions along the leaves "
            "and can defoliate the crop in wet years."
        ),
        spread_mechanism=(
            "Spores spread by wind and rain; the fungus survives on maize residue from "
            "previous crops."
        ),
        severity="moderate",
        watering="Avoid overhead irrigation late in the day; keep leaves dry.",
        sunlight="Full sun; avoid dense sowing.",
        temperature="Cool, humid, wet weather (18-27 C) favours it.",
        humidity="High humidity with wet leaves drives spread.",
        fertilizer="Balanced NPK; avoid excess nitrogen.",
        isolation="Rotate and incorporate maize residue; rogue infected plants.",
        monitoring_advice=(
            "Check leaves for long grey-green lesions along the veins",
            "Scout after wet spells — lesions turn tan-brown with time",
        ),
        recovery_timeline="About 2 weeks with treatment",
        organic=(
            _organic(
                "Neem oil 2%",
                "Foliar spray of 2% neem oil at early lesions.",
                "every 7-10 days",
                category="neem-oil",
            ),
        ),
        chemical=(
            _chem(
                "fungicide",
                "Mancozeb 75% WP",
                "2.5 g per litre of water",
                "at first sign, every 14 days",
            ),
            _chem(
                "fungicide",
                "Propiconazole 25% EC",
                "1 ml per litre of water",
                "every 14 days",
            ),
        ),
    ),
    ("Maize / Corn", "Common Rust"): RecommendationSeed(
        disease_name="Common Rust",
        crop_name="Maize / Corn",
        overview=(
            "A rust disease of maize marked by reddish-brown powdery pustules; usually mild "
            "but it can yellow the leaves early in severe cases."
        ),
        spread_mechanism=(
            "Spores carried long distances by wind; cool damp weather favours infection."
        ),
        severity="low",
        watering="Irrigate normally; avoid prolonged leaf wetness.",
        sunlight="Full sun; moderate plant density.",
        temperature="Cool, damp weather (16-23 C) favours the rust.",
        humidity="High humidity with dew aids infection.",
        fertilizer="Maintain balanced fertility.",
        isolation="Remove heavily infected leaves; plant rust-resistant hybrids.",
        monitoring_advice=(
            "Scout for reddish-brown powdery pustules on both leaf surfaces",
            "Watch for early yellowing and drying of leaves in severe infection",
        ),
        recovery_timeline="1-2 weeks with treatment",
        organic=(
            _organic(
                "Wettable sulphur 0.3%",
                "Spray wettable sulphur 0.3% (3 g/L water) at first pustules.",
                "every 10 days",
                category="bio-fungicide",
            ),
        ),
        chemical=(
            _chem(
                "fungicide",
                "Tebuconazole 25.9% EC",
                "1 ml per litre of water",
                "at onset, repeat after 14 days",
            ),
        ),
    ),
    # ══ Cotton ══════════════════════════════════════════════════════════
    ("Cotton", "Cotton Leaf Curl Virus"): RecommendationSeed(
        disease_name="Cotton Leaf Curl Virus",
        crop_name="Cotton",
        overview=(
            "A virus disease of cotton spread by whitefly. There is no cure — control the "
            "whitefly vector and remove infected plants."
        ),
        spread_mechanism=(
            "Spread by whitefly (Bemisia tabaci); the virus persists in weed hosts and "
            "ratoon cotton."
        ),
        severity="severe",
        watering="Irrigate at boll stage without waterlogging; avoid stress.",
        sunlight="Sow early and synchronised across the village to limit whitefly build-up.",
        temperature="Warm weather favours whitefly; monitor in summer.",
        humidity="Moderate humidity; avoid dense canopies that shelter whitefly.",
        fertilizer="Balanced nutrition; avoid excess nitrogen.",
        isolation="Rogue infected plants immediately; destroy ratoon cotton and weed hosts.",
        monitoring_advice=(
            "Check leaf undersides weekly for whitefly and curled new leaves",
            "Watch for thickened veins and enations under the leaves",
        ),
        recovery_timeline="No cure; manage the vector and rogue infected plants to limit spread",
        organic=(
            _organic(
                "Neem oil 5 ml/L",
                "Spray neem oil 5 ml per litre of water weekly against whitefly.",
                "every 7 days",
                category="neem-oil",
            ),
        ),
        chemical=(
            _chem(
                "insecticide",
                "Imidacloprid 17.8% SL",
                "0.3 ml per litre of water",
                "against whitefly, every 10-14 days",
            ),
            _chem(
                "insecticide",
                "Buprofezin 25% SC",
                "2 ml per litre of water",
                "at peak nymph stage",
            ),
        ),
        prevention_tips=(
            "Use CLCuV-tolerant hybrids",
            "Sow early and synchronised to limit whitefly spread",
            "Destroy weed hosts and ratoon cotton around the field",
        ),
    ),
    ("Cotton", "Boll Rot"): RecommendationSeed(
        disease_name="Boll Rot",
        crop_name="Cotton",
        overview=(
            "A fungal rot of cotton bolls — damage from bollworm and trapped moisture let "
            "the fungus in, ruining the lint."
        ),
        spread_mechanism=(
            "Wet humid weather, bollworm damage and dense canopies that trap moisture inside bolls."
        ),
        severity="moderate",
        watering="Avoid excess irrigation; keep the canopy open.",
        sunlight="Prune to open the canopy; improve airflow.",
        temperature="Warm wet weather favours the rot.",
        humidity="High humidity inside the canopy is the trigger.",
        fertilizer="Avoid excess nitrogen that thickens the canopy.",
        isolation="Harvest opened bolls promptly; remove rotting bolls.",
        monitoring_advice=(
            "Check bolls for water-soaked spots turning brown",
            "Inspect for pink or black fungal growth inside bolls",
        ),
        recovery_timeline="2-3 weeks with management",
        organic=(
            _organic(
                "Neem oil + copper spray",
                "Spray 2% neem oil with copper on developing bolls.",
                "every 10 days",
                category="neem-oil",
            ),
        ),
        chemical=(
            _chem(
                "fungicide",
                "Carbendazim 50% WP",
                "1 g per litre of water",
                "on bolls at first sign",
            ),
        ),
        prevention_tips=(
            "Control bollworm to reduce entry points",
            "Avoid excess nitrogen that thickens the canopy",
            "Harvest opened bolls promptly",
        ),
    ),
    # ══ Chickpea ════════════════════════════════════════════════════════
    ("Chickpea / Chana", "Fusarium Wilt"): RecommendationSeed(
        disease_name="Fusarium Wilt",
        crop_name="Chickpea / Chana",
        overview=(
            "A soil-borne wilt of chickpea that yellows and collapses plants in patches. "
            "Prevention and rogueing matter most — recovery is rare."
        ),
        spread_mechanism=(
            "Soil-borne fungus that persists in fields for years; favoured by warm soils "
            "and low moisture."
        ),
        severity="severe",
        watering="Avoid moisture stress; do not over-irrigate in the podding stage.",
        sunlight="Full sun; plant on well-drained raised beds.",
        temperature="Warm soils favour the fungus.",
        humidity="Moderate; the disease is worse in low-moisture, warm conditions.",
        fertilizer="Low nitrogen (chickpea fixes its own); apply phosphorus and sulphur.",
        isolation="Remove infected plants with roots; rotate with cereals for 3-4 years.",
        monitoring_advice=(
            "Watch for one-sided yellowing and drooping of leaves",
            "Check stems for brown to black vascular discolouration",
        ),
        recovery_timeline="Usually no recovery — prevent and remove infected plants",
        organic=(
            _organic(
                "Trichoderma viride drench",
                "Soil drench with Trichoderma viride 4 g per litre at seedling stage.",
                "at seedling stage",
                category="bio-fungicide",
            ),
            _organic(
                "Pseudomonas fluorescens seed treatment",
                "Treat seed with Pseudomonas fluorescens 10 g per kg.",
                "at sowing",
                category="bio-fungicide",
            ),
        ),
        chemical=(
            _chem(
                "fungicide",
                "Carbendazim 50% WP (seed treatment)",
                "2 g per kg of seed",
                "before sowing",
            ),
            _chem(
                "fungicide",
                "Thiram",
                "3 g per litre of water",
                "drench infected patches",
            ),
        ),
        prevention_tips=(
            "Use wilt-resistant varieties",
            "Rotate with non-host cereal crops for 3-4 years",
            "Treat seed with Trichoderma before sowing",
        ),
    ),
    ("Chickpea / Chana", "Ascochyta Blight"): RecommendationSeed(
        disease_name="Ascochyta Blight",
        crop_name="Chickpea / Chana",
        overview=(
            "A fungal disease of chickpea that makes circular lesions on leaves and pods "
            "and can defoliate the crop in wet weather."
        ),
        spread_mechanism=(
            "Cool humid weather and rain splash spread spores; it is also seed-borne and "
            "survives on crop residues."
        ),
        severity="moderate",
        watering="Avoid overhead irrigation; water at the base early in the day.",
        sunlight="Avoid dense sowing; improve air circulation.",
        temperature="Cool, humid weather favours it.",
        humidity="High humidity with rain splash drives spread.",
        fertilizer="Balanced nutrition; avoid excess nitrogen.",
        isolation="Rotate and bury chickpea stubble; rogue infected plants.",
        monitoring_advice=(
            "Check leaves and pods for pale-brown lesions with dark borders",
            "Look for concentric rings and black dots (pycnidia) in lesions",
        ),
        recovery_timeline="2-3 weeks with treatment",
        organic=(
            _organic(
                "Neem oil 1%",
                "Spray 1% neem oil at first lesions.",
                "every 7-10 days",
                category="neem-oil",
            ),
            _organic(
                "Pseudomonas fluorescens 0.5%",
                "Spray 0.5% Pseudomonas fluorescens at flowering.",
                "at flowering",
                category="bio-fungicide",
            ),
        ),
        chemical=(
            _chem(
                "fungicide",
                "Chlorothalonil 75% WP",
                "2 g per litre of water",
                "at first symptom",
            ),
            _chem(
                "fungicide",
                "Tebuconazole 25.9% EC",
                "1 ml per litre of water",
                "every 12-15 days",
            ),
        ),
    ),
    # ══ Onion ═══════════════════════════════════════════════════════════
    ("Onion", "Purple Blotch"): RecommendationSeed(
        disease_name="Purple Blotch",
        crop_name="Onion",
        overview=(
            "A fungal disease of onion that makes sunken purple blotches on leaves; it can "
            "kill the tops and rot bulbs in storage."
        ),
        spread_mechanism=(
            "Warm humid weather, heavy rains and thrips injury open entry points for the fungus."
        ),
        severity="moderate",
        watering="Ensure good drainage; avoid wetting leaves late in the day.",
        sunlight="Full sun; space rows for airflow.",
        temperature="Warm, humid weather (25-30 C) favours it.",
        humidity="High humidity with leaf wetness drives spread.",
        fertilizer="Balanced nutrition; control thrips to reduce wounds.",
        isolation="Rotate with non-allium crops; remove infected debris.",
        monitoring_advice=(
            "Check leaves for small whitish sunken spots with purple centres",
            "Watch for leaves dying back from the tips",
        ),
        recovery_timeline="About 2 weeks with treatment",
        organic=(
            _organic(
                "Neem oil + copper spray",
                "Spray 1% neem oil with copper at first spots.",
                "every 7-10 days",
                category="neem-oil",
            ),
            _organic(
                "Trichoderma viride",
                "Foliar spray of Trichoderma viride.",
                "every 10 days",
                category="bio-fungicide",
            ),
        ),
        chemical=(
            _chem(
                "fungicide",
                "Mancozeb 75% WP",
                "2.5 g per litre of water",
                "at first sign, every 10 days",
            ),
            _chem(
                "fungicide",
                "Propiconazole 25% EC",
                "1 ml per litre of water",
                "every 10 days",
            ),
        ),
    ),
    ("Onion", "Downy Mildew"): RecommendationSeed(
        disease_name="Downy Mildew",
        crop_name="Onion",
        overview=(
            "A fungal disease of onion that streaks the leaves yellow and covers them in "
            "grey-purple fuzz in wet weather, cutting bulb size."
        ),
        spread_mechanism=(
            "Cool humid nights with wet foliage; the fungus also survives on infected bulbs "
            "in storage."
        ),
        severity="moderate",
        watering="Irrigate early in the day so foliage dries by night.",
        sunlight="Full sun; space rows for ventilation.",
        temperature="Cool, humid weather (10-20 C) favours it.",
        humidity="High humidity and wet leaves drive infection.",
        fertilizer="Balanced nutrition; avoid excess nitrogen.",
        isolation="Use disease-free sets/bulbs; remove infected plants.",
        monitoring_advice=(
            "Check older leaves for pale green to yellow streaks",
            "Look for grey-purple fuzzy growth on lesions in wet weather",
        ),
        recovery_timeline="2-3 weeks with treatment",
        organic=(
            _organic(
                "Copper oxychloride 0.25%",
                "Spray copper oxychloride 0.25% (2.5 g/L water).",
                "weekly in wet weather",
                category="bio-fungicide",
            ),
        ),
        chemical=(
            _chem(
                "fungicide",
                "Metalaxyl + Mancozeb",
                "2.5 g per litre of water",
                "at first sign, every 10 days",
            ),
        ),
    ),
    # ══ Chilli ══════════════════════════════════════════════════════════
    ("Chilli / Chilli pepper", "Anthracnose / Fruit Rot"): RecommendationSeed(
        disease_name="Anthracnose / Fruit Rot",
        crop_name="Chilli / Chilli pepper",
        overview=(
            "A fungal disease of chilli that makes sunken, ringed lesions on fruit and "
            "drops them early; it also rots seed."
        ),
        spread_mechanism=(
            "Warm wet weather, rain splash and infected seed and debris spread the fungus."
        ),
        severity="high",
        watering="Stake plants and prune lower foliage; avoid wetting fruit.",
        sunlight="Full sun; keep the canopy open.",
        temperature="Warm, humid weather (25-30 C) favours it.",
        humidity="High humidity with rain splash drives infection.",
        fertilizer="Balanced NPK; extra calcium helps fruit quality.",
        isolation="Harvest ripe fruit promptly; remove infected fruit and debris.",
        monitoring_advice=(
            "Check fruit for sunken circular lesions with dark rings",
            "Look for pink spore masses on lesions in wet weather",
        ),
        recovery_timeline="About 2 weeks with treatment",
        homemade=(
            _home(
                "Buttermilk + baking soda spray",
                "Mix 2 parts buttermilk with 1 part baking soda in 10 L water; spray the crop.",
                "every 10 days",
                ingredients=("Buttermilk", "Baking soda", "Water 10 L"),
                category="kitchen-ingredients",
            ),
        ),
        organic=(
            _organic(
                "Neem oil + copper oxychloride",
                "Spray 2% neem oil with copper oxychloride at flowering.",
                "at flowering, every 10 days",
                category="neem-oil",
            ),
            _organic(
                "Pseudomonas fluorescens",
                "Foliar spray of Pseudomonas fluorescens.",
                "every 10-14 days",
                category="bio-fungicide",
            ),
        ),
        chemical=(
            _chem(
                "fungicide",
                "Carbendazim 50% WP",
                "1 g per litre of water",
                "at first lesions",
            ),
            _chem(
                "fungicide",
                "Mancozeb 75% WP",
                "2.5 g per litre of water",
                "every 10 days; alternate products",
            ),
        ),
    ),
    ("Chilli / Chilli pepper", "Chilli Leaf Curl"): RecommendationSeed(
        disease_name="Chilli Leaf Curl",
        crop_name="Chilli / Chilli pepper",
        overview=(
            "A virus disease of chilli spread by whitefly; there is no cure, so the plan "
            "is vector control and removing infected plants."
        ),
        spread_mechanism=("Transmitted by whitefly (Bemisia tabaci) feeding on infected plants."),
        severity="severe",
        watering="Keep plants stress-free; avoid excess nitrogen.",
        sunlight="Use reflective plastic mulch to repel whitefly.",
        temperature="Warm weather builds whitefly populations.",
        humidity="Moderate humidity; avoid dense planting.",
        fertilizer="Balanced nutrition; avoid lush new growth that attracts whitefly.",
        isolation="Rogue infected plants early; control weeds hosting whitefly.",
        monitoring_advice=(
            "Check young leaves for curling, puckering and reduced size",
            "Look for whitefly on leaf undersides at the growing tip",
        ),
        recovery_timeline="No cure once infected — manage the vector to limit spread",
        organic=(
            _organic(
                "Neem oil 5 ml/L",
                "Spray neem oil 5 ml per litre of water weekly against whitefly.",
                "every 7 days",
                category="neem-oil",
            ),
        ),
        chemical=(
            _chem(
                "insecticide",
                "Imidacloprid 17.8% SL",
                "0.3 ml per litre of water",
                "against vectors, every 10-14 days",
            ),
        ),
        prevention_tips=(
            "Use virus-tolerant hybrids",
            "Rogue infected plants early",
            "Mulch with reflective plastic to repel whitefly",
        ),
    ),
    # ══ Brinjal ═════════════════════════════════════════════════════════
    ("Brinjal / Eggplant", "Phomopsis Blight"): RecommendationSeed(
        disease_name="Phomopsis Blight",
        crop_name="Brinjal / Eggplant",
        overview=(
            "A fungal disease of brinjal that spots the leaves and rots the fruit, both in "
            "the field and in storage."
        ),
        spread_mechanism=("Warm humid weather; the fungus is seed-borne and soil-borne."),
        severity="moderate",
        watering="Irrigate at the base; avoid wetting fruit.",
        sunlight="Full sun; rotate with non-solanaceous crops.",
        temperature="Warm, humid weather favours it.",
        humidity="High humidity drives infection.",
        fertilizer="Balanced NPK with potassium for fruit quality.",
        isolation="Remove infected fruits and debris; rogue badly hit plants.",
        monitoring_advice=(
            "Check leaves for grey-brown concentric-ring lesions",
            "Watch fruit for sunken brown spots with black specks",
        ),
        recovery_timeline="2-3 weeks with treatment",
        homemade=(
            _home(
                "Neem seed extract spray",
                "Soak neem seed in water overnight, strain and spray weekly.",
                "once a week",
                ingredients=("Neem seeds", "Water"),
                category="traditional",
            ),
        ),
        organic=(
            _organic(
                "Copper oxychloride 0.3%",
                "Spray copper oxychloride 0.3% (3 g/L water).",
                "every 14 days",
                category="bio-fungicide",
            ),
            _organic(
                "Pseudomonas fluorescens",
                "Seed treatment plus foliar spray of Pseudomonas fluorescens.",
                "at sowing and every 14 days",
                category="bio-fungicide",
            ),
        ),
        chemical=(
            _chem(
                "fungicide",
                "Carbendazim 50% WP",
                "1 g per litre of water",
                "at first symptoms",
            ),
            _chem(
                "fungicide",
                "Mancozeb 75% WP",
                "2.5 g per litre of water",
                "as a protectant, every 14 days",
            ),
        ),
    ),
    ("Brinjal / Eggplant", "Little Leaf Disease"): RecommendationSeed(
        disease_name="Little Leaf Disease",
        crop_name="Brinjal / Eggplant",
        overview=(
            "A phytoplasma disease of brinjal that makes leaves small and bushy and stops "
            "fruit set. There is no cure — remove infected plants."
        ),
        spread_mechanism=(
            "Spread by the leafhopper (Hishimonus phycitis) feeding on infected plants."
        ),
        severity="severe",
        watering="Keep plants well watered; avoid stress.",
        sunlight="Full sun; control leafhoppers from the seedling stage.",
        temperature="Warm weather favours the leafhopper vector.",
        humidity="Moderate humidity.",
        fertilizer="Balanced nutrition; healthy plants tolerate it better.",
        isolation="Rogue infected plants immediately to stop the vector.",
        monitoring_advice=(
            "Watch for small, leathery pale-green leaves and bushy branching",
            "Look for flowers turning leafy and fruit failing to set",
        ),
        recovery_timeline="No cure — remove infected plants promptly",
        organic=(
            _organic(
                "Neem oil 2%",
                "Spray 2% neem oil against leafhoppers.",
                "every 7 days",
                category="neem-oil",
            ),
        ),
        chemical=(
            _chem(
                "insecticide",
                "Imidacloprid 17.8% SL",
                "0.3 ml per litre of water",
                "against leafhoppers, every 10-14 days",
            ),
        ),
        prevention_tips=(
            "Rogue infected plants immediately",
            "Control leafhoppers from the seedling stage",
            "Use resistant varieties where available",
        ),
    ),
    # ══ Soybean ═════════════════════════════════════════════════════════
    ("Soybean", "Soybean Rust"): RecommendationSeed(
        disease_name="Soybean Rust",
        crop_name="Soybean",
        overview=(
            "A fast-spreading rust that yellows and strips soybean leaves, causing major "
            "yield loss if it arrives before pod fill."
        ),
        spread_mechanism=(
            "Wind-dispersed spores; the rust favours warm humid weather and survives on "
            "alternate weed hosts."
        ),
        severity="severe",
        watering="Irrigate at pod-fill without waterlogging.",
        sunlight="Full sun; sow early to escape peak rust weather.",
        temperature="Warm humid weather (20-28 C) favours it.",
        humidity="High humidity drives the disease.",
        fertilizer="Balanced phosphorus and sulphur; low nitrogen.",
        isolation="Rogue infected plants; remove alternate weed hosts.",
        monitoring_advice=(
            "Scout lower leaves from flowering onward for tiny tan-to-red lesions",
            "Check leaf undersides for raised pustules",
        ),
        recovery_timeline="About 2 weeks with early treatment",
        organic=(
            _organic(
                "Wettable sulphur 0.3%",
                "Spray wettable sulphur 0.3% (3 g/L water) at first pustules.",
                "every 10 days",
                category="bio-fungicide",
            ),
        ),
        chemical=(
            _chem(
                "fungicide",
                "Tebuconazole 25.9% EC",
                "1 ml per litre of water",
                "at first sign",
            ),
            _chem(
                "fungicide",
                "Azoxystrobin 23% SC",
                "1 ml per litre of water",
                "every 15 days",
            ),
        ),
    ),
    ("Soybean", "Yellow Mosaic"): RecommendationSeed(
        disease_name="Yellow Mosaic",
        crop_name="Soybean",
        overview=(
            "A virus disease of soybean (MYMV) that mottles the leaves yellow and reduces "
            "podding; control the whitefly vector."
        ),
        spread_mechanism=(
            "Transmitted by whitefly; spreads from infected legume fields and weeds."
        ),
        severity="moderate",
        watering="Irrigate normally; avoid water stress.",
        sunlight="Sow early and uniformly; full sun.",
        temperature="Warm weather favours whitefly.",
        humidity="Moderate humidity.",
        fertilizer="Balanced nutrition; avoid excess nitrogen.",
        isolation="Rogue infected plants and control whitefly.",
        monitoring_advice=(
            "Check leaves for bright yellow-green mottling and puckering",
            "Look for whitefly on the underside of young leaves",
        ),
        recovery_timeline="No cure — manage the whitefly vector to limit spread",
        organic=(
            _organic(
                "Neem oil 5 ml/L",
                "Spray neem oil 5 ml per litre of water weekly against whitefly.",
                "every 7 days",
                category="neem-oil",
            ),
        ),
        chemical=(
            _chem(
                "insecticide",
                "Thiamethoxam 25% WG",
                "0.2 g per litre of water",
                "against vectors, every 10-14 days",
            ),
        ),
        prevention_tips=(
            "Use resistant varieties",
            "Sow early and uniformly",
            "Control whitefly and rogue infected plants",
        ),
    ),
    # ══ Groundnut ═══════════════════════════════════════════════════════
    ("Groundnut / Peanut", "Early Leaf Spot"): RecommendationSeed(
        disease_name="Early Leaf Spot",
        crop_name="Groundnut / Peanut",
        overview=(
            "A common fungal leaf spot of groundnut that starts on older leaves; severe "
            "wet spells can defoliate the crop."
        ),
        spread_mechanism=(
            "Warm humid weather, rain splash and infected crop debris spread the spores."
        ),
        severity="moderate",
        watering="Irrigate at peg formation without prolonged leaf wetness.",
        sunlight="Full sun; avoid dense planting.",
        temperature="Warm, humid weather (25-30 C) favours it.",
        humidity="High humidity with rain drives spread.",
        fertilizer="Calcium at pegging; low nitrogen.",
        isolation="Rotate with cereals; incorporate groundnut residue after harvest.",
        monitoring_advice=(
            "Check older leaves for small reddish-brown spots with yellow halos",
            "Watch for defoliation in severe wet spells",
        ),
        recovery_timeline="About 2 weeks with treatment",
        organic=(
            _organic(
                "Neem oil + copper spray",
                "Spray 1% neem oil with copper at first spots.",
                "every 10 days",
                category="neem-oil",
            ),
            _organic(
                "Pseudomonas fluorescens",
                "Foliar spray of Pseudomonas fluorescens.",
                "every 10-14 days",
                category="bio-fungicide",
            ),
        ),
        chemical=(
            _chem(
                "fungicide",
                "Mancozeb 75% WP",
                "2.5 g per litre of water",
                "at first sign, every 12 days",
            ),
            _chem(
                "fungicide",
                "Tebuconazole 25.9% EC",
                "1 ml per litre of water",
                "every 12 days",
            ),
        ),
    ),
    ("Groundnut / Peanut", "Late Leaf Spot"): RecommendationSeed(
        disease_name="Late Leaf Spot",
        crop_name="Groundnut / Peanut",
        overview=(
            "A fungal leaf spot that appears later in the season with small black spots on "
            "both leaf surfaces; it causes heavy defoliation and pod loss."
        ),
        spread_mechanism=(
            "Warm, wet weather late in the season; spores survive on debris and volunteer plants."
        ),
        severity="high",
        watering="Irrigate at grain fill without wetting leaves excessively.",
        sunlight="Full sun; avoid dense planting and excess nitrogen.",
        temperature="Warm, humid weather late in the season.",
        humidity="High humidity drives the disease.",
        fertilizer="Calcium at pegging; balanced nutrition.",
        isolation="Remove volunteer groundnut plants; rogue infected plants.",
        monitoring_advice=(
            "Check both leaf surfaces for small black spots without clear halos",
            "Watch for dense dark spots on leaf undersides",
        ),
        recovery_timeline="2-3 weeks with treatment",
        organic=(
            _organic(
                "Copper oxychloride 0.25%",
                "Spray copper oxychloride 0.25% (2.5 g/L water).",
                "every 14 days",
                category="bio-fungicide",
            ),
            _organic(
                "Bacillus subtilis biofungicide",
                "Foliar spray of a Bacillus subtilis-based biofungicide.",
                "every 10-14 days",
                category="bio-fungicide",
            ),
        ),
        chemical=(
            _chem(
                "fungicide",
                "Chlorothalonil 75% WP",
                "2 g per litre of water",
                "at first sign, every 12 days",
            ),
            _chem(
                "fungicide",
                "Propiconazole 25% EC",
                "1 ml per litre of water",
                "in rotation, every 12 days",
            ),
        ),
    ),
}
