"""Seed catalog for the knowledge base (M1).

India-focused crops and their common diseases, with symptoms, severity,
stages, causes, recovery time, prevention tips and treatment categories
(organic / chemical / homemade / biological). This is the *bootstrapping*
catalog — it grows via the dataset-collection platform (M4) and treatment
engine (M3).

Kept as plain data so the seeder is trivially idempotent and diffable.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class DiseaseSeed:
    name: str
    pathogen_type: str
    symptoms: list[str]
    severity_range: list[str]
    stages: list[str]
    causes: str
    recovery_time: str
    prevention_tips: list[str]
    organic_treatments: list[str] = field(default_factory=list)
    chemical_treatments: list[str] = field(default_factory=list)
    homemade_remedies: list[str] = field(default_factory=list)
    biological_controls: list[str] = field(default_factory=list)


@dataclass
class CropSeed:
    name: str
    common_name: str
    family: str
    season: list[str]
    growth_days: int
    water_needs: str
    fertilizer_needs: str
    image_url: str | None
    diseases: list[DiseaseSeed] = field(default_factory=list)


CROPS: list[CropSeed] = [
    # ── Tomato ───────────────────────────────────────────────────────────
    CropSeed(
        name="tomato",
        common_name="Tomato",
        family="Solanaceae",
        season=["kharif", "rabi", "zaid"],
        growth_days=75,
        water_needs="Moderate; drip irrigation preferred",
        fertilizer_needs="Balanced NPK; extra potassium at fruiting",
        image_url=None,
        diseases=[
            DiseaseSeed(
                name="Early Blight",
                pathogen_type="Fungus (Alternaria solani)",
                symptoms=[
                    "Dark brown concentric-ring spots on older leaves",
                    "Yellowing and die-back of lower leaves first",
                    "Sunken dark lesions on stems and fruit near the calyx",
                ],
                severity_range=["Low", "Moderate", "High"],
                stages=["Seedling", "Vegetative", "Fruiting"],
                causes=(
                    "Warm, humid weather with frequent dew; infected seed or "
                    "overhead irrigation splashing soil onto leaves."
                ),
                recovery_time="2-3 weeks with treatment",
                prevention_tips=[
                    "Rotate with non-solanaceous crops for 2 years",
                    "Avoid overhead irrigation; water at the base",
                    "Space plants for good airflow; stake and prune lower leaves",
                ],
                organic_treatments=[
                    "Spray copper oxychloride 0.25% at 10-12 day intervals",
                    "Neem-based biofungicide foliar spray every 10 days",
                ],
                chemical_treatments=[
                    "Mancozeb 75% WP 2.5 g/L at first sign; repeat fortnightly",
                    "Chlorothalonil 75% WP 2 g/L as a protectant spray",
                ],
                homemade_remedies=[
                    "Baking-soda spray: 1 tsp soda + 1 tsp oil in 1 L water, weekly",
                    "Garlic-pepper tea: soak crushed garlic in water 24h, strain, spray",
                ],
                biological_controls=[
                    "Trichoderma viride soil application 2.5 kg/ha",
                    "Bacillus subtilis-based biofungicide foliar spray",
                ],
            ),
            DiseaseSeed(
                name="Late Blight",
                pathogen_type="Oomycete (Phytophthora infestans)",
                symptoms=[
                    "Large irregular water-soaked grey-green patches on leaves",
                    "White cottony fungal growth on leaf undersides in humid weather",
                    "Brown greasy lesions on fruit and stems that rot quickly",
                ],
                severity_range=["Moderate", "High", "Severe"],
                stages=["Vegetative", "Flowering", "Fruiting"],
                causes=(
                    "Cool (15-22 °C) wet weather; the pathogen survives on debris "
                    "and volunteer potatoes/tomatoes."
                ),
                recovery_time="1-2 weeks if caught early; may destroy crop if severe",
                prevention_tips=[
                    "Use certified disease-free seed/seedlings",
                    "Scout daily after rain; remove and destroy infected plants",
                    "Avoid dense canopies; ensure good ventilation",
                ],
                organic_treatments=[
                    "Copper-based fungicide (0.3%) every 7-10 days in wet weather",
                    "Kelp/seaweed extract foliar spray to harden plants",
                ],
                chemical_treatments=[
                    "Metalaxyl + Mancozeb 68% WG 2.5 g/L at first symptoms",
                    "Cymoxanil + Mancozeb 1.5 g/L; alternate chemistries to avoid resistance",
                ],
                homemade_remedies=[
                    "Neem oil 5 ml/L weekly as a preventive",
                    "Chamomile tea spray to suppress early fungal spread",
                ],
                biological_controls=[
                    "Bacillus subtilis QST 713 foliar applications",
                    "Compost tea with high microbial diversity",
                ],
            ),
            DiseaseSeed(
                name="Tomato Leaf Curl",
                pathogen_type="Virus (Tomato yellow leaf curl virus, TYLCV)",
                symptoms=[
                    "Upward curling and crinkling of young leaves",
                    "Severe stunting, yellowing of leaf margins",
                    "Flower drop and poor fruit set",
                ],
                severity_range=["Moderate", "High"],
                stages=["Seedling", "Vegetative"],
                causes=(
                    "Spread by whitefly (Bemisia tabaci) feeding; persists in "
                    "weed hosts and infected volunteer plants."
                ),
                recovery_time="No cure once infected; manage vector + rogue plants",
                prevention_tips=[
                    "Use resistant varieties; raise seedlings under insect-proof net",
                    "Control whitefly with yellow sticky traps (10-12/ha)",
                    "Rogue and destroy infected plants promptly",
                ],
                organic_treatments=[
                    "Neem oil 5 ml/L every 7 days to suppress whitefly",
                    "Botanical oil sprays (karanj/nim) on leaf undersides",
                ],
                chemical_treatments=[
                    "Imidacloprid 17.8% SL 0.3 ml/L on whitefly hotspots",
                    "Diafenthiuron 50% WP 1.2 g/L as a rotational spray",
                ],
                homemade_remedies=[],
                biological_controls=[
                    "Release parasitoid wasps (Encarsia/Eretmocerus) for whitefly",
                    "Apply Beauveria bassiana 1 kg/ha against nymphs",
                ],
            ),
        ],
    ),
    # ── Potato ───────────────────────────────────────────────────────────
    CropSeed(
        name="potato",
        common_name="Potato",
        family="Solanaceae",
        season=["rabi", "zaid"],
        growth_days=90,
        water_needs="Regular; keep soil evenly moist at tuber initiation",
        fertilizer_needs="High potassium; moderate nitrogen",
        image_url=None,
        diseases=[
            DiseaseSeed(
                name="Late Blight",
                pathogen_type="Oomycete (Phytophthora infestans)",
                symptoms=[
                    "Dark, water-soaked lesions with pale green halos on leaves",
                    "White mildew ring on the underside of lesions",
                    "Brown firm rot on tubers in storage",
                ],
                severity_range=["Moderate", "High", "Severe"],
                stages=["Vegetative", "Tuberization"],
                causes=(
                    "Cool, humid weather and frequent rains; infected seed tubers "
                    "and cull piles are primary sources."
                ),
                recovery_time="1-2 weeks with aggressive treatment",
                prevention_tips=[
                    "Plant certified seed tubers only",
                    "Hill up soil to protect tubers from spores",
                    "Destroy volunteer plants and cull piles",
                ],
                organic_treatments=[
                    "Copper oxychloride 0.25% weekly in wet weather",
                    "Neem oil 3% foliar spray as a preventive",
                ],
                chemical_treatments=[
                    "Metalaxyl + Mancozeb 2.5 g/L at first symptom",
                    "Chlorothalonil 75% WP 2 g/L rotated with mancozeb",
                ],
                homemade_remedies=[
                    "Baking soda + oil spray (1 tsp each in 1 L water)",
                ],
                biological_controls=[
                    "Bacillus subtilis-based products as a protectant",
                ],
            ),
            DiseaseSeed(
                name="Early Blight",
                pathogen_type="Fungus (Alternaria solani)",
                symptoms=[
                    "Target-like brown spots with concentric rings on leaves",
                    "Yellowing and die-back of lower foliage",
                    "Dark, leathery lesions on tubers (dry rot)",
                ],
                severity_range=["Low", "Moderate", "High"],
                stages=["Vegetative", "Tuberization"],
                causes=(
                    "Warm humid conditions and nutrient stress; spores carried on soil and debris."
                ),
                recovery_time="2-3 weeks with treatment",
                prevention_tips=[
                    "Rotate away from solanaceous crops",
                    "Maintain balanced nutrition; avoid excess nitrogen",
                    "Furrow irrigation instead of sprinklers",
                ],
                organic_treatments=[
                    "Copper-based fungicide 0.3% at 10-day intervals",
                ],
                chemical_treatments=[
                    "Mancozeb 75% WP 2.5 g/L fortnightly",
                    "Azoxystrobin 23% SC 1 ml/L for late-season protection",
                ],
                homemade_remedies=[
                    "Neem seed extract foliar spray weekly",
                ],
                biological_controls=[
                    "Trichoderma harzianum seed/soil treatment",
                ],
            ),
        ],
    ),
    # ── Rice ─────────────────────────────────────────────────────────────
    CropSeed(
        name="rice",
        common_name="Paddy / Rice",
        family="Poaceae",
        season=["kharif"],
        growth_days=120,
        water_needs="High; standing water 2-5 cm during most of the season",
        fertilizer_needs="Split nitrogen; zinc and silicon often needed",
        image_url=None,
        diseases=[
            DiseaseSeed(
                name="Rice Blast",
                pathogen_type="Fungus (Magnaporthe oryzae)",
                symptoms=[
                    "Diamond-shaped lesions with grey centres on leaves",
                    "Dark collar rot on the stem at the leaf junction",
                    "Grey neck lesions that break, causing panicle blight",
                ],
                severity_range=["Moderate", "High", "Severe"],
                stages=["Tiller", "Panicle initiation", "Heading"],
                causes=(
                    "High humidity with cool nights; excess nitrogen; dense "
                    "planting; airborne spores travel long distances."
                ),
                recovery_time="2-3 weeks with treatment",
                prevention_tips=[
                    "Use blast-resistant varieties",
                    "Avoid excess nitrogen; split applications",
                    "Maintain even water depth and avoid late planting",
                ],
                organic_treatments=[
                    "Neem cake soil application 200 kg/ha",
                    "Spray Pseudomonas fluorescens 2% at tillering",
                ],
                chemical_treatments=[
                    "Tricyclazole 75% WP 0.6 g/L at first lesions",
                    "Isoprothiolane 40% EC 1.5 ml/L at boot-leaf stage",
                ],
                homemade_remedies=[
                    "Cow-dung slurry with turmeric paste as a prophylactic",
                ],
                biological_controls=[
                    "Seed treatment with Pseudomonas fluorescens 10 g/kg",
                    "Bacillus subtilis foliar sprays",
                ],
            ),
            DiseaseSeed(
                name="Bacterial Leaf Blight",
                pathogen_type="Bacterium (Xanthomonas oryzae pv. oryzae)",
                symptoms=[
                    "Yellowish lesions starting at leaf tips, spreading downward",
                    "Wavy grey-green margins between healthy and diseased tissue",
                    "Milky bacterial ooze on leaves in wet weather",
                ],
                severity_range=["Moderate", "High"],
                stages=["Tiller", "Panicle initiation", "Grain filling"],
                causes=(
                    "Injury from wind/insects; flood irrigation carrying the "
                    "bacterium; infected seed and stubble."
                ),
                recovery_time="2-4 weeks with management",
                prevention_tips=[
                    "Use resistant varieties and clean seed",
                    "Avoid deep flooding during the vegetative stage",
                    "Reduce nitrogen doses at peak tillering",
                ],
                organic_treatments=[],
                chemical_treatments=[
                    "Streptocycline 0.2 g/L + copper oxychloride 0.3%",
                    "Spray copper fungicide at first sign; repeat after 15 days",
                ],
                homemade_remedies=[],
                biological_controls=[],
            ),
            DiseaseSeed(
                name="Sheath Blight",
                pathogen_type="Fungus (Rhizoctonia solani)",
                symptoms=[
                    "Greenish-grey oval lesions on leaf sheaths near the waterline",
                    "Lesions enlarge into irregular blighted patches",
                    "Poor grain fill and chalky kernels",
                ],
                severity_range=["Low", "Moderate", "High"],
                stages=["Tiller", "Panicle initiation", "Grain filling"],
                causes=(
                    "Dense canopy with high humidity; excess nitrogen; infected sclerotia in soil."
                ),
                recovery_time="2-3 weeks with treatment",
                prevention_tips=[
                    "Avoid excess nitrogen and dense sowing",
                    "Drain fields periodically at tillering",
                    "Remove and destroy heavily infected plants",
                ],
                organic_treatments=[
                    "Spray Pseudomonas fluorescens 2% at sheath elongation",
                ],
                chemical_treatments=[
                    "Validamycin 3% L 2.5 ml/L at disease onset",
                    "Hexaconazole 5% EC 2 ml/L at boot stage",
                ],
                homemade_remedies=[],
                biological_controls=[
                    "Bacillus subtilis-based granules at tillering",
                ],
            ),
        ],
    ),
    # ── Wheat ────────────────────────────────────────────────────────────
    CropSeed(
        name="wheat",
        common_name="Wheat",
        family="Poaceae",
        season=["rabi"],
        growth_days=110,
        water_needs="Moderate; 4-5 irrigations at critical stages",
        fertilizer_needs="Nitrogen-rich; zinc for many soils",
        image_url=None,
        diseases=[
            DiseaseSeed(
                name="Leaf Rust",
                pathogen_type="Fungus (Puccinia triticina)",
                symptoms=[
                    "Small orange-brown pustules scattered on leaves",
                    "Pustules rupture to release orange powder (uredospores)",
                    "Premature leaf yellowing and reduced grain weight",
                ],
                severity_range=["Low", "Moderate", "High"],
                stages=["Tillering", "Stem elongation", "Heading"],
                causes=(
                    "Cool moist weather; spores carried long distances by wind; "
                    "overwintering on volunteer wheat."
                ),
                recovery_time="1-2 weeks with treatment",
                prevention_tips=[
                    "Grow rust-resistant varieties",
                    "Remove volunteer wheat and grassy weeds",
                    "Avoid excess nitrogen that promotes lush canopies",
                ],
                organic_treatments=[
                    "Neem oil 1% foliar spray at first pustules",
                ],
                chemical_treatments=[
                    "Propiconazole 25% EC 1 ml/L at first rust",
                    "Tebuconazole 25.9% EC 1 ml/L; repeat after 15 days if needed",
                ],
                homemade_remedies=[],
                biological_controls=[],
            ),
            DiseaseSeed(
                name="Powdery Mildew",
                pathogen_type="Fungus (Blumeria graminis)",
                symptoms=[
                    "White powdery fungal growth on leaves and stems",
                    "Yellowing and browning of heavily covered leaves",
                    "Reduced tillering and shrivelled grain",
                ],
                severity_range=["Low", "Moderate"],
                stages=["Tillering", "Stem elongation", "Heading"],
                causes=(
                    "Cool humid weather with poor airflow; dense sowing; high nitrogen fertility."
                ),
                recovery_time="1-2 weeks with treatment",
                prevention_tips=[
                    "Use tolerant varieties and moderate seeding rate",
                    "Balanced nitrogen; avoid lush growth",
                ],
                organic_treatments=[
                    "Sulphur dust or wettable sulphur 0.3% spray",
                ],
                chemical_treatments=[
                    "Tridemorph 80% EC 0.75 ml/L at first symptoms",
                    "Propiconazole 25% EC 1 ml/L as an alternative",
                ],
                homemade_remedies=[
                    "Milk spray: 1 part milk + 9 parts water, weekly",
                ],
                biological_controls=[],
            ),
        ],
    ),
    # ── Maize ────────────────────────────────────────────────────────────
    CropSeed(
        name="maize",
        common_name="Maize / Corn",
        family="Poaceae",
        season=["kharif", "rabi"],
        growth_days=95,
        water_needs="Moderate; critical at silking and grain-fill",
        fertilizer_needs="Balanced NPK; zinc in deficient soils",
        image_url=None,
        diseases=[
            DiseaseSeed(
                name="Northern Corn Leaf Blight",
                pathogen_type="Fungus (Setosphaeria turcica)",
                symptoms=[
                    "Long grey-green elliptical lesions along leaf veins",
                    "Lesions turn tan-brown with time",
                    "Defoliation reduces yield if weather is wet",
                ],
                severity_range=["Low", "Moderate", "High"],
                stages=["Vegetative", "Silking", "Grain fill"],
                causes=(
                    "Cool, humid, wet weather; spores spread by wind; residue "
                    "from previous maize crops."
                ),
                recovery_time="2 weeks with treatment",
                prevention_tips=[
                    "Use resistant hybrids",
                    "Rotate and incorporate maize residue",
                    "Avoid overhead irrigation late in the day",
                ],
                organic_treatments=[
                    "Neem oil 2% foliar spray at early lesions",
                ],
                chemical_treatments=[
                    "Mancozeb 75% WP 2.5 g/L at first sign",
                    "Propiconazole 25% EC 1 ml/L; repeat after 14 days",
                ],
                homemade_remedies=[],
                biological_controls=[],
            ),
            DiseaseSeed(
                name="Common Rust",
                pathogen_type="Fungus (Puccinia sorghi)",
                symptoms=[
                    "Reddish-brown powdery pustules on both leaf surfaces",
                    "Severe infection yellows and dries leaves early",
                ],
                severity_range=["Low", "Moderate"],
                stages=["Vegetative", "Silking"],
                causes=("Cool, damp weather; spores carried by wind over long distances."),
                recovery_time="1-2 weeks with treatment",
                prevention_tips=[
                    "Plant rust-resistant hybrids",
                    "Maintain balanced fertility",
                ],
                organic_treatments=[
                    "Wettable sulphur 0.3% spray at first pustules",
                ],
                chemical_treatments=[
                    "Tebuconazole 25.9% EC 1 ml/L at onset",
                ],
                homemade_remedies=[],
                biological_controls=[],
            ),
        ],
    ),
    # ── Cotton ────────────────────────────────────────────────────────────
    CropSeed(
        name="cotton",
        common_name="Cotton",
        family="Malvaceae",
        season=["kharif"],
        growth_days=160,
        water_needs="Moderate; avoid waterlogging, irrigate at boll stage",
        fertilizer_needs="High potassium; nitrogen in splits",
        image_url=None,
        diseases=[
            DiseaseSeed(
                name="Cotton Leaf Curl Virus",
                pathogen_type="Virus (Cotton leaf curl virus, CLCuV)",
                symptoms=[
                    "Upward and downward curling of leaves",
                    "Thickened veins and small leaf-like enations on the underside",
                    "Severe stunting and reduced boll formation",
                ],
                severity_range=["Moderate", "High", "Severe"],
                stages=["Vegetative", "Squaring", "Boll formation"],
                causes=(
                    "Spread by whitefly (Bemisia tabaci); the virus persists in "
                    "weed hosts and ratoon cotton."
                ),
                recovery_time="No cure; manage vector and rogue infected plants",
                prevention_tips=[
                    "Use CLCuV-tolerant hybrids",
                    "Sow early and synchronised across the village to limit whitefly",
                    "Rogue infected plants; control whitefly nymphs",
                ],
                organic_treatments=[
                    "Neem oil 5 ml/L weekly for whitefly suppression",
                ],
                chemical_treatments=[
                    "Imidacloprid 17.8% SL 0.3 ml/L against whitefly",
                    "Buprofezin 25% SC 2 ml/L at peak nymphs",
                ],
                homemade_remedies=[],
                biological_controls=[
                    "Release Chrysoperla / predatory bugs for whitefly",
                    "Apply Beauveria bassiana 1 kg/ha",
                ],
            ),
            DiseaseSeed(
                name="Boll Rot",
                pathogen_type="Fungal complex (Aspergillus, Fusarium, etc.)",
                symptoms=[
                    "Water-soaked spots on bolls that turn brown and rotten",
                    "Pink or black fungal growth inside the boll",
                    "Stained, matted lint that is not harvestable",
                ],
                severity_range=["Low", "Moderate", "High"],
                stages=["Boll formation", "Boll opening"],
                causes=(
                    "Wet humid weather, bollworm damage, and dense canopies "
                    "trapping moisture inside bolls."
                ),
                recovery_time="2-3 weeks with management",
                prevention_tips=[
                    "Control bollworm to reduce entry points",
                    "Avoid excess nitrogen that thickens canopy",
                    "Harvest opened bolls promptly",
                ],
                organic_treatments=[
                    "Neem oil 2% + copper spray on developing bolls",
                ],
                chemical_treatments=[
                    "Carbendazim 50% WP 1 g/L on bolls at first sign",
                ],
                homemade_remedies=[],
                biological_controls=[],
            ),
        ],
    ),
    # ── Chickpea ─────────────────────────────────────────────────────────
    CropSeed(
        name="chickpea",
        common_name="Chickpea / Chana",
        family="Fabaceae",
        season=["rabi"],
        growth_days=100,
        water_needs="Low; avoid excess moisture after flowering",
        fertilizer_needs="Low nitrogen (fixes own); phosphorus and sulphur",
        image_url=None,
        diseases=[
            DiseaseSeed(
                name="Fusarium Wilt",
                pathogen_type="Fungus (Fusarium oxysporum f. sp. ciceris)",
                symptoms=[
                    "Yellowing and drooping of leaves, often on one side first",
                    "Brown to black discolouration of vascular tissue in the stem",
                    "Plants wilt and collapse in patches in the field",
                ],
                severity_range=["Moderate", "High", "Severe"],
                stages=["Seedling", "Flowering", "Podding"],
                causes=(
                    "Soil-borne fungus persisting in fields for years; favoured "
                    "by warm soils and low moisture."
                ),
                recovery_time="Usually no recovery; prevent + remove infected plants",
                prevention_tips=[
                    "Use wilt-resistant varieties",
                    "Rotate with non-host crops (cereals) for 3-4 years",
                    "Treat seed with Trichoderma before sowing",
                ],
                organic_treatments=[
                    "Soil drench with Trichoderma viride 4 g/L at seedling stage",
                ],
                chemical_treatments=[
                    "Seed treatment with carbendazim 2 g/kg",
                    "Drench thiram 3 g/L in infected patches",
                ],
                homemade_remedies=[],
                biological_controls=[
                    "Seed treatment with Pseudomonas fluorescens 10 g/kg",
                ],
            ),
            DiseaseSeed(
                name="Ascochyta Blight",
                pathogen_type="Fungus (Ascochyta rabiei)",
                symptoms=[
                    "Circular pale-brown lesions with dark borders on leaves and pods",
                    "Concentric rings within lesions; pycnidia (black dots)",
                    "Stem girdling and severe defoliation in wet weather",
                ],
                severity_range=["Low", "Moderate", "High"],
                stages=["Vegetative", "Flowering", "Podding"],
                causes=(
                    "Cool humid weather and rain splash; seed-borne infection; "
                    "infected crop residues."
                ),
                recovery_time="2-3 weeks with treatment",
                prevention_tips=[
                    "Use clean, disease-free seed",
                    "Rotate and bury chickpea stubble",
                    "Avoid dense sowing; improve air circulation",
                ],
                organic_treatments=[
                    "Neem oil 1% spray at first lesions",
                ],
                chemical_treatments=[
                    "Chlorothalonil 75% WP 2 g/L at first symptom",
                    "Tebuconazole 25.9% EC 1 ml/L; repeat after 12-15 days",
                ],
                homemade_remedies=[],
                biological_controls=[
                    "Spray Pseudomonas fluorescens 0.5% at flowering",
                ],
            ),
        ],
    ),
    # ── Onion ────────────────────────────────────────────────────────────
    CropSeed(
        name="onion",
        common_name="Onion",
        family="Amaryllidaceae",
        season=["rabi", "kharif"],
        growth_days=100,
        water_needs="Moderate; stop irrigation at bulb maturity",
        fertilizer_needs="High potassium and sulphur; phosphorus at planting",
        image_url=None,
        diseases=[
            DiseaseSeed(
                name="Purple Blotch",
                pathogen_type="Fungus (Alternaria porri)",
                symptoms=[
                    "Small whitish sunken spots on leaves with purple centres",
                    "Lesions enlarge into concentric purple-brown blotches",
                    "Leaves die back; bulbs may rot in storage",
                ],
                severity_range=["Low", "Moderate", "High"],
                stages=["Vegetative", "Bulb formation"],
                causes=("Warm humid weather, heavy rains and thrips injury opening entry points."),
                recovery_time="2 weeks with treatment",
                prevention_tips=[
                    "Control thrips to reduce wounds",
                    "Rotate with non-allium crops",
                    "Ensure good field drainage and airflow",
                ],
                organic_treatments=[
                    "Neem oil 1% + copper spray at first spots",
                ],
                chemical_treatments=[
                    "Mancozeb 75% WP 2.5 g/L at first sign",
                    "Propiconazole 25% EC 1 ml/L; repeat after 10 days",
                ],
                homemade_remedies=[],
                biological_controls=[
                    "Trichoderma viride foliar spray",
                ],
            ),
            DiseaseSeed(
                name="Downy Mildew",
                pathogen_type="Oomycete (Peronospora destructor)",
                symptoms=[
                    "Pale green to yellow streaks on older leaves",
                    "Grey-purple fuzzy growth on lesions in wet weather",
                    "Leaf collapse and poor bulb size",
                ],
                severity_range=["Low", "Moderate", "High"],
                stages=["Vegetative", "Bulb formation"],
                causes=("Cool humid nights with wet foliage; infected bulbs in storage."),
                recovery_time="2-3 weeks with treatment",
                prevention_tips=[
                    "Use disease-free sets/bulbs",
                    "Irrigate early so foliage dries by night",
                    "Space rows for ventilation",
                ],
                organic_treatments=[
                    "Copper oxychloride 0.25% weekly in wet weather",
                ],
                chemical_treatments=[
                    "Metalaxyl + Mancozeb 2.5 g/L at first sign",
                ],
                homemade_remedies=[],
                biological_controls=[],
            ),
        ],
    ),
    # ── Chilli ───────────────────────────────────────────────────────────
    CropSeed(
        name="chilli",
        common_name="Chilli / Chilli pepper",
        family="Solanaceae",
        season=["kharif", "rabi"],
        growth_days=90,
        water_needs="Moderate; consistent moisture at flowering",
        fertilizer_needs="Balanced NPK; extra calcium to prevent blossom-end rot",
        image_url=None,
        diseases=[
            DiseaseSeed(
                name="Anthracnose / Fruit Rot",
                pathogen_type="Fungus (Colletotrichum capsici)",
                symptoms=[
                    "Sunken circular lesions with dark concentric rings on fruit",
                    "Pink spore masses on lesions in wet weather",
                    "Premature fruit drop and seed rot",
                ],
                severity_range=["Moderate", "High"],
                stages=["Flowering", "Fruiting"],
                causes=("Warm wet weather; rain splash; infected seed and debris."),
                recovery_time="2 weeks with treatment",
                prevention_tips=[
                    "Use disease-free seed; treat seed with hot water",
                    "Stake plants and prune lower foliage",
                    "Harvest ripe fruit promptly",
                ],
                organic_treatments=[
                    "Neem oil 2% + copper oxychloride spray at flowering",
                ],
                chemical_treatments=[
                    "Carbendazim 50% WP 1 g/L at first lesions",
                    "Mancozeb 75% WP 2.5 g/L; alternate products",
                ],
                homemade_remedies=[
                    "Buttermilk + baking soda spray (2:1 in 10 L water)",
                ],
                biological_controls=[
                    "Pseudomonas fluorescens foliar sprays",
                ],
            ),
            DiseaseSeed(
                name="Chilli Leaf Curl",
                pathogen_type="Virus (Chilli leaf curl virus)",
                symptoms=[
                    "Leaf curling, puckering and reduced leaf size",
                    "Yellowing, stunting and profuse branching",
                    "Flower drop and severe yield loss",
                ],
                severity_range=["Moderate", "High", "Severe"],
                stages=["Vegetative", "Flowering"],
                causes=("Transmitted by whitefly (Bemisia tabaci) feeding on infected plants."),
                recovery_time="No cure once infected; manage vector",
                prevention_tips=[
                    "Use virus-tolerant hybrids",
                    "Rogue infected plants early",
                    "Mulch with reflective plastic to repel whitefly",
                ],
                organic_treatments=[
                    "Neem oil 5 ml/L weekly against whitefly",
                ],
                chemical_treatments=[
                    "Imidacloprid 17.8% SL 0.3 ml/L against vectors",
                ],
                homemade_remedies=[],
                biological_controls=[
                    "Beauveria bassiana 1 kg/ha for whitefly nymphs",
                ],
            ),
        ],
    ),
    # ── Brinjal ──────────────────────────────────────────────────────────
    CropSeed(
        name="brinjal",
        common_name="Brinjal / Eggplant",
        family="Solanaceae",
        season=["kharif", "rabi"],
        growth_days=95,
        water_needs="Moderate; regular moisture at fruit set",
        fertilizer_needs="Balanced NPK with potassium for fruit quality",
        image_url=None,
        diseases=[
            DiseaseSeed(
                name="Phomopsis Blight",
                pathogen_type="Fungus (Phomopsis vexans)",
                symptoms=[
                    "Grey-brown concentric-ring lesions on leaves",
                    "Large sunken brown spots with black specks on fruit",
                    "Fruit rot in storage; stem cankers on young plants",
                ],
                severity_range=["Low", "Moderate", "High"],
                stages=["Seedling", "Vegetative", "Fruiting"],
                causes=("Warm humid weather; seed-borne and soil-borne fungus."),
                recovery_time="2-3 weeks with treatment",
                prevention_tips=[
                    "Use disease-free seed and treat before sowing",
                    "Rotate with non-solanaceous crops",
                    "Remove infected fruits and debris",
                ],
                organic_treatments=[
                    "Copper oxychloride 0.3% spray fortnightly",
                ],
                chemical_treatments=[
                    "Carbendazim 50% WP 1 g/L at first symptoms",
                    "Mancozeb 75% WP 2.5 g/L as protectant",
                ],
                homemade_remedies=[
                    "Neem seed extract spray weekly",
                ],
                biological_controls=[
                    "Pseudomonas fluorescens seed + foliar application",
                ],
            ),
            DiseaseSeed(
                name="Little Leaf Disease",
                pathogen_type="Phytoplasma",
                symptoms=[
                    "Leaves become small, leathery and pale green",
                    "Excessive bushy branching; shortened internodes",
                    "Flowers become leafy and fruit rarely sets",
                ],
                severity_range=["Moderate", "High", "Severe"],
                stages=["Vegetative", "Flowering"],
                causes=("Spread by leafhopper (Hishimonus phycitis) on infected plants."),
                recovery_time="No cure; remove infected plants",
                prevention_tips=[
                    "Rogue infected plants immediately",
                    "Control leafhoppers from the seedling stage",
                    "Use resistant varieties where available",
                ],
                organic_treatments=[
                    "Neem oil 2% spray against leafhoppers",
                ],
                chemical_treatments=[
                    "Imidacloprid 17.8% SL 0.3 ml/L against leafhoppers",
                ],
                homemade_remedies=[],
                biological_controls=[],
            ),
        ],
    ),
    # ── Soybean ──────────────────────────────────────────────────────────
    CropSeed(
        name="soybean",
        common_name="Soybean",
        family="Fabaceae",
        season=["kharif"],
        growth_days=100,
        water_needs="Moderate; critical at pod-fill",
        fertilizer_needs="Low nitrogen; phosphorus and sulphur",
        image_url=None,
        diseases=[
            DiseaseSeed(
                name="Soybean Rust",
                pathogen_type="Fungus (Phakopsora pachyrhizi)",
                symptoms=[
                    "Tiny tan to reddish-brown lesions on lower leaves",
                    "Leaf undersides with raised pustules",
                    "Rapid yellowing and defoliation, high yield loss",
                ],
                severity_range=["Moderate", "High", "Severe"],
                stages=["Flowering", "Pod development", "Grain fill"],
                causes=(
                    "Wind-dispersed spores; favours warm humid weather; survives "
                    "on alternate weed hosts."
                ),
                recovery_time="2 weeks with early treatment",
                prevention_tips=[
                    "Scout lower leaves from flowering onward",
                    "Use resistant varieties",
                    "Sow early to escape peak rust weather",
                ],
                organic_treatments=[
                    "Wettable sulphur 0.3% at first pustules",
                ],
                chemical_treatments=[
                    "Tebuconazole 25.9% EC 1 ml/L at first sign",
                    "Azoxystrobin 23% SC 1 ml/L; repeat after 15 days",
                ],
                homemade_remedies=[],
                biological_controls=[],
            ),
            DiseaseSeed(
                name="Yellow Mosaic",
                pathogen_type="Virus (Mungbean yellow mosaic virus, MYMV)",
                symptoms=[
                    "Bright yellow and green mottling on leaves",
                    "Puckering and slight leaf curling",
                    "Delayed flowering and fewer pods",
                ],
                severity_range=["Low", "Moderate", "High"],
                stages=["Vegetative", "Flowering", "Pod development"],
                causes=("Transmitted by whitefly; spreads from infected legume fields and weeds."),
                recovery_time="No cure; manage whitefly vector",
                prevention_tips=[
                    "Use resistant varieties",
                    "Sow early and uniformly",
                    "Control whitefly and rogue infected plants",
                ],
                organic_treatments=[
                    "Neem oil 5 ml/L weekly against whitefly",
                ],
                chemical_treatments=[
                    "Thiamethoxam 25% WG 0.2 g/L against vectors",
                ],
                homemade_remedies=[],
                biological_controls=[],
            ),
        ],
    ),
    # ── Groundnut ────────────────────────────────────────────────────────
    CropSeed(
        name="groundnut",
        common_name="Groundnut / Peanut",
        family="Fabaceae",
        season=["kharif", "rabi"],
        growth_days=110,
        water_needs="Moderate; critical at peg formation",
        fertilizer_needs="Calcium at pegging; low nitrogen",
        image_url=None,
        diseases=[
            DiseaseSeed(
                name="Early Leaf Spot",
                pathogen_type="Fungus (Cercospora arachidicola)",
                symptoms=[
                    "Small reddish-brown spots with yellow halos on older leaves",
                    "Spots darken and enlarge with age",
                    "Defoliation in severe wet spells",
                ],
                severity_range=["Low", "Moderate", "High"],
                stages=["Vegetative", "Pegging", "Grain fill"],
                causes=("Warm humid weather; rain splash; infected crop debris."),
                recovery_time="2 weeks with treatment",
                prevention_tips=[
                    "Rotate with cereals",
                    "Use tolerant varieties",
                    "Incorporate groundnut residue after harvest",
                ],
                organic_treatments=[
                    "Neem oil 1% + copper spray at first spots",
                ],
                chemical_treatments=[
                    "Mancozeb 75% WP 2.5 g/L at first sign",
                    "Tebuconazole 25.9% EC 1 ml/L; repeat after 12 days",
                ],
                homemade_remedies=[],
                biological_controls=[
                    "Pseudomonas fluorescens foliar sprays",
                ],
            ),
            DiseaseSeed(
                name="Late Leaf Spot",
                pathogen_type="Fungus (Phaeoisariopsis personata)",
                symptoms=[
                    "Small black spots without clear halos, on both leaf surfaces",
                    "Leaf undersides covered with dense dark spots",
                    "Severe premature defoliation and pod loss",
                ],
                severity_range=["Low", "Moderate", "High", "Severe"],
                stages=["Vegetative", "Pegging", "Grain fill"],
                causes=("Warm, wet weather late in the season; spores on debris and volunteers."),
                recovery_time="2-3 weeks with treatment",
                prevention_tips=[
                    "Use resistant varieties",
                    "Avoid dense planting and excess nitrogen",
                    "Remove volunteer groundnut plants",
                ],
                organic_treatments=[
                    "Copper oxychloride 0.25% spray fortnightly",
                ],
                chemical_treatments=[
                    "Chlorothalonil 75% WP 2 g/L at first sign",
                    "Propiconazole 25% EC 1 ml/L in rotation",
                ],
                homemade_remedies=[],
                biological_controls=[
                    "Bacillus subtilis-based biofungicides",
                ],
            ),
        ],
    ),
]
