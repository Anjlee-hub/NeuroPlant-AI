"""Curated soil-recommendation catalog (M3, Task 3).

Soil guidance for every crop in the M1 knowledge catalog (``app.db.seed_data``),
keyed by crop common name for idempotent seeding. Each crop carries a complete
soil profile — the nine guidance areas, crop-fit suitability, a baseline
soil-health rating, and improvement suggestions — plus optional disease-aware
notes (how each of the crop's diseases interacts with soil) and severity-aware
notes/suggestions.

The seeder builds one ``SoilRecommendation`` row per catalog disease by merging
the crop profile with the disease note (if any). Because a soil plan belongs to
a crop's disease, the advice is both crop-appropriate and disease-aware. Adding
a new disease = a ``disease_notes`` entry (or nothing, which the seeder covers
by fallback); new signals like weather/location/soil-test data extend the
request context, not this schema.

Written for Indian field conditions: pH ranges and nutrient guidance follow
state-agriculture extension literature. Advice is guidance, not a prescription.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# Bump when the catalog content changes; the seeder activates a new version.
SOIL_VERSION = "v1"


@dataclass(frozen=True)
class SoilSeed:
    """Complete soil guidance for one crop (merged per disease at seed time)."""

    crop_name: str
    recommended_soil_type: str
    ph_range: str
    moisture_level: str
    drainage: str
    organic_matter: str
    npk: str
    micronutrients: tuple[str, ...] = ()
    compost: str = ""
    mulching: str = ""
    soil_suitability: str = ""
    base_soil_health: str = "good"  # excellent | good | fair | poor
    improvement_suggestions: tuple[str, ...] = ()
    # Disease name -> how the disease interacts with soil.
    disease_notes: dict[str, str] = field(default_factory=dict)
    # Severity label -> note / extra improvement suggestions.
    severity_notes: dict[str, str] = field(default_factory=dict)
    severity_suggestions: dict[str, tuple[str, ...]] = field(default_factory=dict)


SOIL_BY_CROP: dict[str, SoilSeed] = {
    # ══ Tomato ══════════════════════════════════════════════════════════
    "Tomato": SoilSeed(
        crop_name="Tomato",
        recommended_soil_type="Deep, well-drained sandy loam",
        ph_range="6.0 – 6.8",
        moisture_level="Moderate and even; avoid waterlogging",
        drainage="Excellent — raised beds where heavy rain is common",
        organic_matter="3–5%; enrich with compost before planting",
        npk="Balanced NPK; potassium during fruit set, low early nitrogen",
        micronutrients=("Calcium", "Magnesium", "Boron"),
        compost="15–20 t/ha well-rotted FYM or compost worked into the bed",
        mulching=(
            "Black plastic or straw mulch saves water and stops soil splashing spores "
            "onto leaves"
        ),
        soil_suitability=(
            "Tomato grows best in deep, well-drained sandy-loam soil with pH 6.0–6.8 "
            "and good organic matter."
        ),
        base_soil_health="good",
        improvement_suggestions=(
            "Raise beds 20–25 cm to keep roots above standing water",
            "Get a soil test before adding fertiliser — balance NPK first",
        ),
        disease_notes={
            "Early Blight": (
                "Early Blight survives in the soil on crop debris — rotate away from "
                "tomato/potato for 2 years and plough debris under after harvest."
            ),
            "Late Blight": (
                "Late Blight thrives in wet, poorly drained soil; improve drainage and "
                "water at the base in the morning to keep the bed drier."
            ),
            "Tomato Leaf Curl": (
                "Leaf Curl spreads through whiteflies that breed on weeds and wet mulch "
                "— keep the bed weed-free and avoid dense over-mulching."
            ),
        },
        severity_notes={
            "severe": "Severe attack — restore soil balance before replanting.",
            "moderate": "Keep soil evenly moist and continue mulching to reduce stress.",
        },
        severity_suggestions={
            "severe": (
                "Solarise or replace the top soil in badly infested beds before the next crop",
                "Apply a micronutrient foliar spray to help plants recover",
            ),
            "moderate": (
                "Top-dress with potassium to strengthen recovering plants",
            ),
        },
    ),
    # ══ Potato ══════════════════════════════════════════════════════════
    "Potato": SoilSeed(
        crop_name="Potato",
        recommended_soil_type="Loose, well-drained sandy loam to loam",
        ph_range="5.0 – 6.5",
        moisture_level="Even moisture at tuber initiation; keep soil moist but not soggy",
        drainage="Excellent — avoid any standing water around tubers",
        organic_matter="2–4%; bulky organic matter keeps the soil loose",
        npk="High potassium, moderate nitrogen; avoid excess nitrogen late",
        micronutrients=("Zinc", "Boron", "Iron"),
        compost="12–15 t/ha well-rotted FYM at land preparation",
        mulching="Light straw mulch after earthing-up to hold moisture and keep tubers shaded",
        soil_suitability=(
            "Potato prefers loose, well-drained sandy-loam soil with pH 5.0–6.5; compact "
            "or waterlogged soil distorts tubers."
        ),
        base_soil_health="good",
        improvement_suggestions=(
            "Deep plough and level the field to avoid water pooling in hollows",
            "Earthing-up keeps soil loose and tubers protected",
        ),
        disease_notes={
            "Late Blight": (
                "Late Blight flourishes in cool, wet soil and spreads via splashing water "
                "— ridge the rows, drain well and never irrigate over the foliage."
            ),
            "Early Blight": (
                "Early Blight spores persist in infected soil and debris; rotate to "
                "non-solanaceous crops for 2–3 years and plough residue under."
            ),
        },
        severity_notes={
            "severe": "Severe attack — treat soil-borne inoculum before the next season.",
            "moderate": "Keep moisture even and avoid stressing plants with dry-wet swings.",
        },
        severity_suggestions={
            "severe": (
                "Rotate away from potato and tomato for at least 3 years",
                "Test soil pH and correct towards 5.5–6.0 for tuber health",
            ),
            "moderate": (
                "Top-dress with potassium to strengthen plants",
            ),
        },
    ),
    # ══ Paddy / Rice ════════════════════════════════════════════════════
    "Paddy / Rice": SoilSeed(
        crop_name="Paddy / Rice",
        recommended_soil_type="Clay loam with good water-holding capacity",
        ph_range="5.5 – 7.0",
        moisture_level="Standing water 2–5 cm for most of the season; drain before harvest",
        drainage="Controlled flooding; good bunds and a drainage outlet",
        organic_matter="Green manuring (dhaincha/sunhemp) improves paddy soil",
        npk="Nitrogen in splits; zinc and silicon commonly needed",
        micronutrients=("Zinc", "Iron", "Silicon"),
        compost="10–15 t/ha FYM; green manure before transplanting",
        mulching="Straw mulch on raised beds for upland rice; not needed in puddled fields",
        soil_suitability=(
            "Rice grows best in clay-loam paddy soil that holds water (pH 5.5–7.0); "
            "sandy soil loses water too quickly."
        ),
        base_soil_health="good",
        improvement_suggestions=(
            "Apply zinc to paddy soil — zinc deficiency is common in rice belts",
            "Level the field so water depth stays uniform",
        ),
        disease_notes={
            "Rice Blast": (
                "Blast is worse with excess nitrogen and drought stress — split nitrogen "
                "and keep water levels even so roots are not stressed."
            ),
            "Bacterial Leaf Blight": (
                "Bacterial blight spreads in standing water through wounds — drain fields "
                "periodically and avoid excess nitrogen."
            ),
            "Sheath Blight": (
                "Sheath Blight favours dense, wet canopies — avoid over-dense planting and "
                "reduce water depth during the worst part of the season."
            ),
        },
        severity_notes={
            "severe": "Severe attack — manage water and nitrogen before the next season.",
            "moderate": "Keep water depth steady; avoid drought-flood swings.",
        },
        severity_suggestions={
            "severe": (
                "Drain the field fully for 3–5 days to break disease cycles",
                "Add silica-rich amendments (rice husk ash) to harden plants",
            ),
            "moderate": (
                "Split nitrogen into 3 doses to avoid lush, susceptible growth",
            ),
        },
    ),
    # ══ Wheat ════════════════════════════════════════════════════════════
    "Wheat": SoilSeed(
        crop_name="Wheat",
        recommended_soil_type="Well-drained loam to clay loam",
        ph_range="6.0 – 7.5",
        moisture_level="Moderate; 4–5 irrigations at critical stages",
        drainage="Good — wheat dislikes prolonged waterlogging",
        organic_matter="2–3%; crop residue incorporation feeds the soil",
        npk="Nitrogen-rich; zinc for many soils",
        micronutrients=("Zinc", "Copper", "Iron"),
        compost="5–10 t/ha FYM or compost before sowing",
        mulching="Stubble/straw mulch conserves moisture and suppresses weeds",
        soil_suitability=(
            "Wheat does best in well-drained loam to clay-loam soil with pH 6.0–7.5; "
            "waterlogged soils reduce tillering."
        ),
        base_soil_health="good",
        improvement_suggestions=(
            "Test soil for zinc and add 5 kg/ha zinc sulphate where deficient",
            "Avoid flood irrigation on light soils — use border/check basins",
        ),
        disease_notes={
            "Leaf Rust": (
                "Rust spores overwinter on wheat debris in the soil — rotate and plough "
                "stubble under to reduce early infection."
            ),
            "Powdery Mildew": (
                "Mildew thrives in humid, sheltered canopies — avoid over-dense sowing "
                "and do not over-water late in the season."
            ),
        },
        severity_notes={
            "severe": "Severe attack — clean field residue and plan rotation.",
            "moderate": "Maintain steady moisture; avoid stress at heading.",
        },
        severity_suggestions={
            "severe": (
                "Plough stubble and volunteer wheat under before the next season",
                "Apply a balanced NPK top-dressing to aid recovery",
            ),
            "moderate": (
                "Irrigate on time to avoid moisture stress during grain fill",
            ),
        },
    ),
    # ══ Maize / Corn ═════════════════════════════════════════════════════
    "Maize / Corn": SoilSeed(
        crop_name="Maize / Corn",
        recommended_soil_type="Deep, well-drained sandy loam to loam",
        ph_range="5.5 – 7.0",
        moisture_level="Moderate; critical at silking and grain-fill",
        drainage="Good — maize roots dislike waterlogging",
        organic_matter="1.5–3%; compost before planting improves nutrient release",
        npk="Balanced NPK; zinc on deficient soils",
        micronutrients=("Zinc", "Boron", "Iron"),
        compost="10–12 t/ha FYM or compost at land preparation",
        mulching="Straw mulch around the rows holds moisture in summer",
        soil_suitability=(
            "Maize thrives in deep, well-drained sandy-loam soil with pH 5.5–7.0; "
            "compacted or waterlogged soil stunts the crop."
        ),
        base_soil_health="good",
        improvement_suggestions=(
            "Break hard pans with deep ploughing — maize roots are sensitive to compaction",
            "Apply zinc at planting where deficiency is known",
        ),
        disease_notes={
            "Northern Corn Leaf Blight": (
                "The blight survives on crop residue — rotate maize, plough stubble under "
                "and improve soil drainage in heavy soils."
            ),
            "Common Rust": (
                "Rust spreads in humid weather — avoid over-dense stands and keep "
                "nitrogen balanced (excess N makes plants susceptible)."
            ),
        },
        severity_notes={
            "severe": "Severe attack — rotate and clean residue before replanting.",
            "moderate": "Maintain even moisture and balanced nutrition.",
        },
        severity_suggestions={
            "severe": (
                "Rotate away from maize for 2 years to break the residue cycle",
                "Add potassium to harden plants against rust/blight",
            ),
            "moderate": (
                "Top-dress with nitrogen at the right stage only",
            ),
        },
    ),
    # ══ Cotton ═══════════════════════════════════════════════════════════
    "Cotton": SoilSeed(
        crop_name="Cotton",
        recommended_soil_type="Deep, well-drained black (regur) to loam",
        ph_range="6.0 – 8.0",
        moisture_level="Moderate; avoid waterlogging, irrigate at boll stage",
        drainage="Critical — cotton roots rot in standing water",
        organic_matter="1.5–2.5%; green manuring improves black-soil tilth",
        npk="High potassium; nitrogen in splits",
        micronutrients=("Zinc", "Boron", "Magnesium"),
        compost="8–10 t/ha FYM; green manure (sunhemp) before sowing",
        mulching="Straw or plastic mulch around rows conserves moisture",
        soil_suitability=(
            "Cotton prefers deep, well-drained black (regur) or loamy soil with pH "
            "6.0–8.0; waterlogged soil causes root rot."
        ),
        base_soil_health="good",
        improvement_suggestions=(
            "Provide drainage channels in low-lying fields — cotton hates standing water",
            "Test for boron and zinc before sowing on black soils",
        ),
        disease_notes={
            "Cotton Leaf Curl Virus": (
                "Leaf Curl spreads through whiteflies; reduce soil splash, control weeds "
                "and avoid dense over-mulching that shelters the pest."
            ),
            "Boll Rot": (
                "Boll rot follows high humidity and waterlogged soil — improve drainage "
                "and stop irrigation once bolls open."
            ),
        },
        severity_notes={
            "severe": "Severe attack — restore drainage and rotate before replanting.",
            "moderate": "Keep the field well-drained; avoid late irrigation.",
        },
        severity_suggestions={
            "severe": (
                "Provide field drainage and ridge sowing for the next crop",
                "Apply potash to strengthen plants against rot",
            ),
            "moderate": (
                "Stop irrigation as bolls open to lower humidity",
            ),
        },
    ),
    # ══ Chickpea / Chana ═════════════════════════════════════════════════
    "Chickpea / Chana": SoilSeed(
        crop_name="Chickpea / Chana",
        recommended_soil_type="Light sandy loam to clay loam",
        ph_range="6.0 – 7.5",
        moisture_level="Low — avoid excess moisture after flowering",
        drainage="Excellent — chickpea is very sensitive to waterlogging",
        organic_matter="1.5–3%; modest organic matter is enough",
        npk="Low nitrogen (fixes its own); phosphorus and sulphur",
        micronutrients=("Boron", "Molybdenum", "Zinc"),
        compost="5–8 t/ha well-rotted compost; avoid fresh manure",
        mulching="Light mulch or stubble retention keeps soil cool and moist",
        soil_suitability=(
            "Chickpea suits light sandy-loam to clay-loam soil with pH 6.0–7.5 and "
            "excellent drainage; it cannot survive waterlogging."
        ),
        base_soil_health="fair",
        improvement_suggestions=(
            "Ensure field drainage — chickpea dies in standing water",
            "Seed treatment with rhizobium improves nitrogen fixing in poor soils",
        ),
        disease_notes={
            "Fusarium Wilt": (
                "Wilt is a classic soil-borne disease — it persists in infected soil for "
                "years; rotate, solarise and improve drainage."
            ),
            "Ascochyta Blight": (
                "Blight spreads from infected seed and debris in moist soil — use clean "
                "seed, rotate and avoid waterlogging."
            ),
        },
        severity_notes={
            "severe": "Severe attack — treat soil-borne inoculum before the next season.",
            "moderate": "Keep the field drained and avoid irrigating late.",
        },
        severity_suggestions={
            "severe": (
                "Solarise seed-bed soil for 3–4 weeks before sowing",
                "Rotate to cereals for 2–3 years to starve soil-borne wilt",
            ),
            "moderate": (
                "Apply sulphur top-dressing to support recovery",
            ),
        },
    ),
    # ══ Onion ════════════════════════════════════════════════════════════
    "Onion": SoilSeed(
        crop_name="Onion",
        recommended_soil_type="Loose, well-drained sandy loam",
        ph_range="6.0 – 6.8",
        moisture_level="Moderate; stop irrigation at bulb maturity",
        drainage="Good — bulbs rot in heavy, wet soil",
        organic_matter="2–3%; well-rotted compost loosens the soil",
        npk="High potassium and sulphur; phosphorus at planting",
        micronutrients=("Sulphur", "Boron", "Manganese"),
        compost="8–10 t/ha well-rotted compost before transplanting",
        mulching="Straw mulch keeps moisture even and suppresses weeds",
        soil_suitability=(
            "Onion prefers loose, well-drained sandy-loam soil with pH 6.0–6.8; heavy "
            "soil produces misshapen bulbs and rot."
        ),
        base_soil_health="fair",
        improvement_suggestions=(
            "Ridges or raised beds stop bulb rot in heavy rain",
            "Sulphur nutrition improves bulb size and storage life",
        ),
        disease_notes={
            "Purple Blotch": (
                "Purple Blotch thrives in humid, moist conditions — avoid dense planting "
                "and over-head irrigation late in the day."
            ),
            "Downy Mildew": (
                "Downy Mildew spreads in wet, cool weather — ensure good drainage, avoid "
                "wet foliage and rotate away from onion family crops."
            ),
        },
        severity_notes={
            "severe": "Severe attack — stop irrigation early and improve airflow.",
            "moderate": "Keep leaves dry; water at the base in the morning.",
        },
        severity_suggestions={
            "severe": (
                "Stop irrigation to dry the canopy and bulbs",
                "Rotate away from onion/garlic for 2 years",
            ),
            "moderate": (
                "Irrigate in the morning so foliage dries by night",
            ),
        },
    ),
    # ══ Chilli / Chilli pepper ═══════════════════════════════════════════
    "Chilli / Chilli pepper": SoilSeed(
        crop_name="Chilli / Chilli pepper",
        recommended_soil_type="Well-drained sandy loam to loam",
        ph_range="6.0 – 7.0",
        moisture_level="Moderate; consistent moisture at flowering",
        drainage="Good — chilli dislikes waterlogging",
        organic_matter="2–3%; compost before transplanting",
        npk="Balanced NPK; extra calcium to prevent blossom-end rot",
        micronutrients=("Calcium", "Magnesium", "Boron"),
        compost="10–12 t/ha FYM or compost at land preparation",
        mulching="Straw or black mulch keeps soil warm and moisture steady",
        soil_suitability=(
            "Chilli grows best in well-drained sandy-loam to loam soil with pH 6.0–7.0 "
            "and steady moisture."
        ),
        base_soil_health="good",
        improvement_suggestions=(
            "Apply lime/dolomite where calcium is low — it prevents blossom-end rot",
            "Mulch to keep moisture steady during flowering",
        ),
        disease_notes={
            "Anthracnose / Fruit Rot": (
                "Anthracnose spores splash from soil onto low fruit — stake plants, "
                "mulch to stop splashing and rotate away from chilli."
            ),
            "Chilli Leaf Curl": (
                "Leaf Curl spreads through whiteflies; reduce soil splash, clear weeds "
                "and keep beds well-drained."
            ),
        },
        severity_notes={
            "severe": "Severe attack — clean residue and restore soil balance.",
            "moderate": "Maintain steady moisture to avoid fruit drop.",
        },
        severity_suggestions={
            "severe": (
                "Stake plants and mulch to keep fruit off the soil",
                "Add calcium (lime) before the next crop",
            ),
            "moderate": (
                "Top-dress with potassium for better fruit set",
            ),
        },
    ),
    # ══ Brinjal / Eggplant ═══════════════════════════════════════════════
    "Brinjal / Eggplant": SoilSeed(
        crop_name="Brinjal / Eggplant",
        recommended_soil_type="Well-drained sandy loam to loam",
        ph_range="5.5 – 7.0",
        moisture_level="Moderate; regular moisture at fruit set",
        drainage="Good — brinjal dislikes waterlogging",
        organic_matter="2–3%; compost before planting",
        npk="Balanced NPK with potassium for fruit quality",
        micronutrients=("Calcium", "Boron", "Magnesium"),
        compost="12–15 t/ha FYM or compost at land preparation",
        mulching="Straw or plastic mulch conserves moisture and blocks soil splash",
        soil_suitability=(
            "Brinjal prefers well-drained sandy-loam to loam soil with pH 5.5–7.0 and "
            "steady moisture."
        ),
        base_soil_health="good",
        improvement_suggestions=(
            "Raised beds prevent waterlogging during monsoon",
            "Top-dress with potassium for glossy, healthy fruit",
        ),
        disease_notes={
            "Phomopsis Blight": (
                "Phomopsis survives in the soil on infected debris and spreads by "
                "splashing water — rotate and keep beds clean."
            ),
            "Little Leaf Disease": (
                "Little Leaf spreads through leafhoppers; keep the bed weed-free and "
                "manage irrigation to reduce pest shelter."
            ),
        },
        severity_notes={
            "severe": "Severe attack — clean field residue and rotate.",
            "moderate": "Keep moisture steady during fruit set.",
        },
        severity_suggestions={
            "severe": (
                "Rotate away from solanaceous crops for 2 years",
                "Plough infected debris under after harvest",
            ),
            "moderate": (
                "Top-dress with potassium to support fruiting",
            ),
        },
    ),
    # ══ Soybean ══════════════════════════════════════════════════════════
    "Soybean": SoilSeed(
        crop_name="Soybean",
        recommended_soil_type="Well-drained loam to sandy loam",
        ph_range="6.0 – 7.0",
        moisture_level="Moderate; critical at pod-fill",
        drainage="Good — soybean is very sensitive to waterlogging",
        organic_matter="2–3%; keep pH near neutral for nodulation",
        npk="Low nitrogen (fixes its own); phosphorus and sulphur",
        micronutrients=("Molybdenum", "Boron", "Zinc"),
        compost="5–8 t/ha well-rotted compost; avoid excess nitrogen",
        mulching="Stubble/mulch retention keeps soil cool and moist",
        soil_suitability=(
            "Soybean prefers well-drained loam with near-neutral pH 6.0–7.0; acidic or "
            "waterlogged soils block nodulation."
        ),
        base_soil_health="fair",
        improvement_suggestions=(
            "Correct acidic soil with lime so rhizobium can nodulate",
            "Ensure field drainage — soybean yields crash on wet soil",
        ),
        disease_notes={
            "Soybean Rust": (
                "Rust spreads fast in humid, moist weather — avoid over-dense sowing and "
                "drain low spots that keep the canopy wet."
            ),
            "Yellow Mosaic": (
                "Yellow Mosaic spreads through whiteflies; control weeds and soil splash, "
                "and avoid over-mulching that shelters the pest."
            ),
        },
        severity_notes={
            "severe": "Severe attack — manage water and rotation before replanting.",
            "moderate": "Keep canopy dry; avoid late-night irrigation.",
        },
        severity_suggestions={
            "severe": (
                "Rotate away from soybean for 2 years to break rust cycles",
                "Improve drainage in low-lying patches",
            ),
            "moderate": (
                "Irrigate in the morning so foliage dries by night",
            ),
        },
    ),
    # ══ Groundnut / Peanut ═══════════════════════════════════════════════
    "Groundnut / Peanut": SoilSeed(
        crop_name="Groundnut / Peanut",
        recommended_soil_type="Loose, well-drained sandy loam",
        ph_range="5.5 – 7.0",
        moisture_level="Moderate; critical at peg formation",
        drainage="Excellent — peg and pod development need loose, dry soil",
        organic_matter="1.5–2.5%; avoid heavy manuring that boosts foliage",
        npk="Calcium at pegging; low nitrogen",
        micronutrients=("Calcium", "Boron", "Molybdenum"),
        compost="5–8 t/ha well-rotted compost; avoid fresh manure",
        mulching="Light straw mulch keeps the pod zone cool and moist",
        soil_suitability=(
            "Groundnut needs loose, well-drained sandy-loam soil with pH 5.5–7.0; heavy "
            "or waterlogged soil ruins pod development."
        ),
        base_soil_health="good",
        improvement_suggestions=(
            "Lime acidic soils so calcium is available for pod-filling",
            "Deep plough the field so pegs can penetrate easily",
        ),
        disease_notes={
            "Early Leaf Spot": (
                "Leaf-spot spores survive on infected crop debris in the soil — rotate, "
                "plough residue under and avoid dense canopies."
            ),
            "Late Leaf Spot": (
                "Late Leaf Spot thrives in humid, wet canopies — improve airflow, avoid "
                "over-watering and rotate away from groundnut."
            ),
        },
        severity_notes={
            "severe": "Severe attack — clean debris and rotate before the next season.",
            "moderate": "Keep moisture steady at peg formation.",
        },
        severity_suggestions={
            "severe": (
                "Rotate away from groundnut for 2 years to break the leaf-spot cycle",
                "Plough infected haulm under after harvest",
            ),
            "moderate": (
                "Apply calcium (gypsum) at pegging to support pod fill",
            ),
        },
    ),
}
