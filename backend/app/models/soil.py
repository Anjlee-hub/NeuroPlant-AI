"""Soil recommendation catalog (M3, Task 3).

Versioned, data-driven soil-intelligence knowledge base, mirroring the
treatment catalog (``app.models.recommendation``). A ``SoilRecommendationCatalog``
groups one or more ``SoilRecommendation`` rows under a version string; exactly
one catalog is active at a time and ``SoilRecommendationService`` resolves every
request against it, so a version bump is atomic from the API's point of view.

A ``SoilRecommendation`` holds the complete beginner-friendly soil guidance for
one disease in the active catalog — the nine guidance areas (soil type, pH,
moisture, drainage, organic matter, NPK, micronutrients, compost, mulching)
plus the crop-fit / soil-health profile (suitability, base health, improvement
suggestions) and disease-aware notes. Severity-aware content is stored as JSON
dicts keyed by severity (``low`` | ``moderate`` | ``severe``) so the service can
merge it at request time without any hardcoded advice in controllers.

Guidance is crop-appropriate *and* disease-aware because each row belongs to one
catalog disease (which in turn belongs to one crop). Future signals — weather,
location, and real soil-test data — extend the request context, not this schema.
"""

from sqlalchemy import JSON, Boolean, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.models.base import TimestampMixin
from app.models.catalog import Disease


class SoilRecommendationCatalog(Base, TimestampMixin):
    __tablename__ = "soil_recommendation_catalogs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    version: Mapped[str] = mapped_column(String(32), unique=True, index=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    recommendations: Mapped[list["SoilRecommendation"]] = relationship(
        back_populates="catalog",
        cascade="all, delete-orphan",
    )


class SoilRecommendation(Base, TimestampMixin):
    __tablename__ = "soil_recommendations"
    __table_args__ = (
        UniqueConstraint("catalog_id", "disease_id", name="uq_soil_catalog_disease"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    catalog_id: Mapped[int] = mapped_column(
        ForeignKey("soil_recommendation_catalogs.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    disease_id: Mapped[int] = mapped_column(
        ForeignKey("diseases.id", ondelete="CASCADE"), index=True, nullable=False
    )

    # ── The nine soil guidance areas ────────────────────────────────────
    recommended_soil_type: Mapped[str | None] = mapped_column(Text, nullable=True)
    ph_range: Mapped[str | None] = mapped_column(String(40), nullable=True)
    moisture_level: Mapped[str | None] = mapped_column(Text, nullable=True)
    drainage: Mapped[str | None] = mapped_column(Text, nullable=True)
    organic_matter: Mapped[str | None] = mapped_column(Text, nullable=True)
    npk: Mapped[str | None] = mapped_column(Text, nullable=True)
    micronutrients: Mapped[list | None] = mapped_column(JSON, nullable=True)
    compost: Mapped[str | None] = mapped_column(Text, nullable=True)
    mulching: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ── Soil-health profile ─────────────────────────────────────────────
    # How well the recommended soil fits the crop (display sentence).
    soil_suitability: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Baseline soil-health rating under good conditions (excellent|good|fair|poor).
    base_soil_health: Mapped[str | None] = mapped_column(String(20), nullable=True)
    improvement_suggestions: Mapped[list | None] = mapped_column(JSON, nullable=True)

    # ── Disease-aware soil advice ───────────────────────────────────────
    # How the detected disease interacts with soil (e.g. waterlogging worsens
    # Phytophthora). Content lives in the seed catalog, not in controllers.
    disease_soil_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Severity-aware content, keyed by severity label:
    #   severity_notes:      {"severe": "…", "moderate": "…"}
    #   severity_suggestions:{"severe": ["…", "…"]}
    severity_notes: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    severity_suggestions: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    catalog: Mapped["SoilRecommendationCatalog"] = relationship(back_populates="recommendations")
    disease: Mapped["Disease"] = relationship()
