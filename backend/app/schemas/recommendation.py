"""Treatment recommendation schemas (M3, Task 1).

Response DTOs for the recommendation engine. The nested item schemas
(:class:`HomemadeRemedyOut`, :class:`OrganicRemedyOut`,
:class:`ChemicalRecommendationOut`) give each treatment category a stable,
structured shape — the client renders them without parsing prose. Everything
comes back as one self-contained :class:`DiseaseRecommendationOut` payload so a
farmers' phone can show the whole care plan in a single screen.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

# Category vocabularies — keep them as constants so seeds and docs agree.
HOMEMADE_CATEGORIES = ("kitchen-ingredients", "homemade-spray", "traditional")
ORGANIC_CATEGORIES = ("neem-oil", "bio-fungicide", "organic-pesticide", "organic-nutrient")
CHEMICAL_CATEGORIES = ("fungicide", "insecticide", "bactericide")


class HomemadeRemedyOut(BaseModel):
    """One homemade remedy (kitchen ingredients / homemade spray / traditional)."""

    title: str = Field(description="Short name, e.g. 'Baking-soda spray'")
    category: str = Field(
        description="kitchen-ingredients | homemade-spray | traditional", default="homemade-spray"
    )
    ingredients: list[str] = Field(
        default_factory=list, description="Simple, affordable ingredients most homes have"
    )
    instructions: str = Field(description="How to prepare and apply it")
    frequency: str = Field(description="How often to apply, e.g. 'once a week'")


class OrganicRemedyOut(BaseModel):
    """One organic/biological remedy (neem oil, bio-fungicide, organic pesticide, nutrient)."""

    title: str = Field(description="Short name, e.g. 'Neem oil foliar spray'")
    category: str = Field(
        description="neem-oil | bio-fungicide | organic-pesticide | organic-nutrient",
        default="bio-fungicide",
    )
    application: str = Field(description="How to prepare and apply it, incl. dose")
    frequency: str = Field(description="How often to apply, e.g. 'every 7 days'")


class ChemicalRecommendationOut(BaseModel):
    """One chemical product with dosage, interval and safety precautions."""

    category: str = Field(description="fungicide | insecticide | bactericide", default="fungicide")
    product: str = Field(description="Product name + formulation, e.g. 'Mancozeb 75% WP'")
    dosage: str = Field(description="Application rate, e.g. '2.5 g per litre of water'")
    application_interval: str = Field(
        description="How long between sprays, e.g. 'every 10-12 days'"
    )
    safety_precautions: list[str] = Field(
        default_factory=list, description="Plain-language safety steps for the farmer"
    )


class RecommendationDiseaseOut(BaseModel):
    """The disease a recommendation plan belongs to (with its crop for context)."""

    id: int = Field(description="Catalog disease id")
    name: str = Field(description="Disease name as the AI reports it")
    crop_id: int | None = Field(default=None, description="Catalog crop id")
    crop_name: str | None = Field(default=None, description="Crop display name")


class DiseaseRecommendationOut(BaseModel):
    """GET /recommendations/diseases/{id} — the full treatment plan for a disease.

    Self-contained: the client needs no other call to render a care plan. Lists
    are empty (never null) so the frontend can map over them safely.
    """

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "catalog_version": "v1",
                    "disease": {
                        "id": 2,
                        "name": "Late Blight",
                        "crop_id": 1,
                        "crop_name": "Tomato",
                    },
                    "overview": "A fast-spreading fungal disease that can destroy a crop "
                    "within days in cool, wet weather.",
                    "cause": "Oomycete (Phytophthora infestans); survives on debris "
                    "and volunteer plants.",
                    "symptoms": [
                        "Dark water-soaked lesions on leaves",
                        "White cottony growth on leaf undersides in humidity",
                    ],
                    "severity": "moderate",
                    "spread_mechanism": "Spores travel on wind, rain splash and "
                    "contaminated tools; worst in cool wet weather.",
                    "homemade_remedies": [
                        {
                            "title": "Baking-soda spray",
                            "category": "homemade-spray",
                            "ingredients": ["Baking soda 1 tsp", "Oil 1 tsp", "Water 1 L"],
                            "instructions": "Mix well and spray every leaf, both sides.",
                            "frequency": "once a week",
                        }
                    ],
                    "organic_remedies": [
                        {
                            "title": "Neem oil foliar spray",
                            "category": "neem-oil",
                            "application": "Mix 5 ml neem oil in 1 L water with a drop "
                            "of soap; spray all surfaces.",
                            "frequency": "every 7-10 days",
                        }
                    ],
                    "chemical_recommendations": [
                        {
                            "category": "fungicide",
                            "product": "Metalaxyl + Mancozeb 68% WG",
                            "dosage": "2.5 g per litre of water",
                            "application_interval": "every 7-10 days in wet weather",
                            "safety_precautions": [
                                "Wear gloves and a mask while spraying",
                                "Keep children and animals away for 24 hours",
                            ],
                        }
                    ],
                    "fertilizer": "Withhold nitrogen; apply potassium to harden the plant.",
                    "watering": "Water at the base early in the morning; avoid wetting leaves.",
                    "sunlight": "Ensure full sun and good airflow between plants.",
                    "temperature": "Manage under 15-22 C risk window; avoid cool shaded spots.",
                    "humidity": "Improve ventilation to keep foliage dry.",
                    "prevention_tips": [
                        "Use certified disease-free seed/seedlings",
                        "Remove and destroy infected plants",
                    ],
                    "recovery_timeline": "1-2 weeks if caught early; may destroy crop if severe.",
                    "isolation": "Remove infected plants and keep a buffer from healthy rows.",
                    "monitoring_advice": [
                        "Scout daily after rain",
                        "Check leaf undersides for white growth",
                    ],
                }
            ]
        },
    )

    catalog_version: str = Field(description="Recommendation catalog version (e.g. 'v1')")
    disease: RecommendationDiseaseOut
    overview: str | None
    cause: str | None
    symptoms: list[str] = Field(default_factory=list)
    severity: str | None
    spread_mechanism: str | None

    homemade_remedies: list[HomemadeRemedyOut] = Field(default_factory=list)
    organic_remedies: list[OrganicRemedyOut] = Field(default_factory=list)
    chemical_recommendations: list[ChemicalRecommendationOut] = Field(default_factory=list)
    fertilizer: str | None

    watering: str | None
    sunlight: str | None
    temperature: str | None
    humidity: str | None

    prevention_tips: list[str] = Field(default_factory=list)
    recovery_timeline: str | None
    isolation: str | None
    monitoring_advice: list[str] = Field(default_factory=list)


class RecommendationCatalogOut(BaseModel):
    """GET /recommendations/catalog — metadata for one catalog version."""

    version: str
    description: str | None
    is_active: bool
    disease_count: int = Field(description="Recommendation plans in this catalog")
    updated_at: datetime
