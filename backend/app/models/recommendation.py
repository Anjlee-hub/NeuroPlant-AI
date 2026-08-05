"""Treatment recommendation catalog (M3, Task 1).

Versioned, data-driven recommendation knowledge base. A ``RecommendationCatalog``
groups one or more ``DiseaseRecommendation`` rows under a version string (e.g.
``v1``); exactly one catalog is active at a time and the service resolves every
request against it, so bumping a version (or activating a new one) is atomic
from the API's point of view.

A ``DiseaseRecommendation`` holds the complete, beginner-friendly treatment
guidance for one disease in the active catalog: disease-level facts (overview,
cause, symptoms, severity, spread mechanism) plus the twelve guidance categories
(homemade / organic / chemical / fertilizer / watering / sunlight / temperature /
humidity / prevention / recovery / isolation / monitoring).

Repeatable entries (symptoms, remedies, chemicals, prevention tips, monitoring
advice) are stored as JSON lists so new items are pure data — the same approach
the catalog models use. Nothing here is hardcoded in controllers: the seeder
loads the curated catalog (``app.db.recommendation_seed_data``) into these rows
and ``RecommendationService`` only ever reads the database.
"""

from sqlalchemy import JSON, Boolean, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.models.base import TimestampMixin
from app.models.catalog import Disease


class RecommendationCatalog(Base, TimestampMixin):
    __tablename__ = "recommendation_catalogs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    version: Mapped[str] = mapped_column(String(32), unique=True, index=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    recommendations: Mapped[list["DiseaseRecommendation"]] = relationship(
        back_populates="catalog",
        cascade="all, delete-orphan",
    )


class DiseaseRecommendation(Base, TimestampMixin):
    __tablename__ = "disease_recommendations"
    __table_args__ = (
        UniqueConstraint("catalog_id", "disease_id", name="uq_recommendation_catalog_disease"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    catalog_id: Mapped[int] = mapped_column(
        ForeignKey("recommendation_catalogs.id", ondelete="CASCADE"), index=True, nullable=False
    )
    disease_id: Mapped[int] = mapped_column(
        ForeignKey("diseases.id", ondelete="CASCADE"), index=True, nullable=False
    )

    # ── Disease-level facts ────────────────────────────────────────────
    overview: Mapped[str | None] = mapped_column(Text, nullable=True)
    cause: Mapped[str | None] = mapped_column(Text, nullable=True)
    symptoms: Mapped[list | None] = mapped_column(JSON, nullable=True)
    severity: Mapped[str | None] = mapped_column(String(40), nullable=True)
    spread_mechanism: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ── Treatment categories ───────────────────────────────────────────
    homemade_remedies: Mapped[list | None] = mapped_column(JSON, nullable=True)
    organic_remedies: Mapped[list | None] = mapped_column(JSON, nullable=True)
    chemical_recommendations: Mapped[list | None] = mapped_column(JSON, nullable=True)
    fertilizer: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ── Environment guidance ───────────────────────────────────────────
    watering: Mapped[str | None] = mapped_column(Text, nullable=True)
    sunlight: Mapped[str | None] = mapped_column(Text, nullable=True)
    temperature: Mapped[str | None] = mapped_column(Text, nullable=True)
    humidity: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ── Ongoing care ───────────────────────────────────────────────────
    prevention_tips: Mapped[list | None] = mapped_column(JSON, nullable=True)
    recovery_timeline: Mapped[str | None] = mapped_column(Text, nullable=True)
    isolation: Mapped[str | None] = mapped_column(Text, nullable=True)
    monitoring_advice: Mapped[list | None] = mapped_column(JSON, nullable=True)

    catalog: Mapped["RecommendationCatalog"] = relationship(back_populates="recommendations")
    disease: Mapped["Disease"] = relationship()
