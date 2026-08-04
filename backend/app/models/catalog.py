"""Knowledge-catalog models: crops and diseases (with remedies as JSON).

Treatment detail lives on ``diseases`` for M1 (seed catalog). The dedicated
``treatments`` / ``fertilizers`` / ``pesticides`` tables arrive in M3 with the
Treatment Recommendation Engine.
"""

from sqlalchemy import JSON, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.models.base import TimestampMixin


class Crop(Base, TimestampMixin):
    __tablename__ = "crops"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    common_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    family: Mapped[str | None] = mapped_column(String(80), nullable=True)
    season: Mapped[list | None] = mapped_column(JSON, nullable=True)  # ["kharif", ...]
    growth_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    water_needs: Mapped[str | None] = mapped_column(String(120), nullable=True)
    fertilizer_needs: Mapped[str | None] = mapped_column(String(120), nullable=True)
    image_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    diseases: Mapped[list["Disease"]] = relationship(
        back_populates="crop", cascade="all, delete-orphan"
    )


class Disease(Base, TimestampMixin):
    __tablename__ = "diseases"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    crop_id: Mapped[int] = mapped_column(ForeignKey("crops.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(160), index=True)
    pathogen_type: Mapped[str | None] = mapped_column(String(60), nullable=True)
    symptoms: Mapped[list | None] = mapped_column(JSON, nullable=True)
    severity_range: Mapped[list | None] = mapped_column(JSON, nullable=True)
    stages: Mapped[list | None] = mapped_column(JSON, nullable=True)
    causes: Mapped[str | None] = mapped_column(Text, nullable=True)
    recovery_time: Mapped[str | None] = mapped_column(String(120), nullable=True)
    prevention_tips: Mapped[list | None] = mapped_column(JSON, nullable=True)
    organic_treatments: Mapped[list | None] = mapped_column(JSON, nullable=True)
    chemical_treatments: Mapped[list | None] = mapped_column(JSON, nullable=True)
    homemade_remedies: Mapped[list | None] = mapped_column(JSON, nullable=True)
    biological_controls: Mapped[list | None] = mapped_column(JSON, nullable=True)

    crop: Mapped["Crop"] = relationship(back_populates="diseases")
