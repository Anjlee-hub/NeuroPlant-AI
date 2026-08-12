"""Rule-based disease-risk engine (M5, Task 1).

Provider-independent: the engine consumes only the normalized
:class:`~app.services.weather.WeatherData` produced by any
:class:`~app.services.weather.WeatherProvider`, so it behaves identically with
the live OpenWeather source, the deterministic mock, or a future regional
provider.

The engine reuses the existing crop/disease catalog
(:mod:`app.models.catalog`) rather than duplicating disease definitions: it
reads each disease's ``pathogen_type`` and applies *documented weather-rule
constants* per pathogen class (fungal / bacterial / viral / phytoplasma). The
composite risk score is the weighted sum of four weather factors (humidity,
temperature, rainfall, wind), each mapped to a favorability in [0, 1] by the
class profile; the level is derived from the score via documented thresholds.

No persistence here: the assessment is stateless over the current weather.
Historical weather records (yield prediction) and outbreak aggregation are
later M5 tasks that will consume the same :class:`WeatherData` seam.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.logging import get_logger
from app.models.catalog import Crop, Disease
from app.schemas.catalog import CropOut
from app.schemas.weather import DiseaseRiskOut, RiskFactorOut, WeatherRiskOut
from app.services.weather import WeatherData, weather_to_out

logger = get_logger(__name__)


class CropNotFoundError(Exception):
    """The requested crop is not in the catalog (an unsupported crop)."""


# ── Risk policy (documented constants — not magic numbers) ────────────────
# Pathogen classes are derived from the catalog's free-text ``pathogen_type``
# (see :func:`pathogen_class`). Each class maps every weather factor to a
# favorability profile; profiles are one of:
#   ramp_up(x, lo, hi)    0 below lo → 1 at/above hi
#   ramp_down(x, at, hi) 1 below/at → 0 at/above hi
#   triangle(x, lo, plo, phi, hi)  plateau across [plo, phi]
#   flat(value)           constant (used for unknown classes)

# Factor weights — sum to 1.0, scaling each favorability into the 0–100 score.
FACTOR_WEIGHTS: dict[str, float] = {
    "humidity": 0.35,
    "temperature": 0.30,
    "rainfall": 0.20,
    "wind": 0.15,
}

# Relative-humidity (%) profiles per class. High RH + leaf wetness favor
# fungal/bacterial disease; vector-borne pathogens peak at mid humidity.
HUMIDITY_PROFILES: dict[str, tuple] = {
    "fungal": ("ramp_up", 55.0, 85.0),
    "bacterial": ("ramp_up", 55.0, 85.0),
    "viral": ("triangle", 30.0, 55.0, 75.0, 90.0),
    "phytoplasma": ("triangle", 30.0, 55.0, 75.0, 90.0),
    "unknown": ("flat", 0.5),
}

# Optimal temperature bands (°C) per class. Favorability is 1 inside the band
# and ramps linearly to 0 ``TEMP_SHOULDER_DEG`` outside it.
TEMPERATURE_BANDS: dict[str, tuple[float, float]] = {
    "fungal": (18.0, 30.0),
    "bacterial": (24.0, 35.0),
    "viral": (24.0, 33.0),
    "phytoplasma": (25.0, 33.0),
    "unknown": (15.0, 35.0),
}
TEMP_SHOULDER_DEG: float = 6.0

# Rainfall (mm in the observation window) profiles per class.
RAINFALL_PROFILES: dict[str, tuple] = {
    # Rain splash + leaf wetness spread fungal/bacterial disease.
    "fungal": ("ramp_up", 0.0, 5.0),
    "bacterial": ("ramp_up", 0.0, 5.0),
    # Heavy rain suppresses vector activity.
    "viral": ("ramp_down", 0.0, 10.0),
    "phytoplasma": ("ramp_down", 0.0, 10.0),
    "unknown": ("flat", 0.5),
}

# Wind (m/s) profiles per class.
WIND_PROFILES: dict[str, tuple] = {
    # Still air lets spores settle on leaves.
    "fungal": ("ramp_down", 1.0, 6.0),
    # Light-moderate wind aids wound/splash spread of bacteria.
    "bacterial": ("triangle", 0.5, 2.0, 5.0, 8.0),
    # Strong wind stops vector flight.
    "viral": ("ramp_down", 2.0, 6.0),
    "phytoplasma": ("ramp_down", 2.0, 6.0),
    "unknown": ("flat", 0.5),
}

# Contribution thresholds for labelling a factor's impact on the risk.
IMPACT_RAISES: float = 0.6
IMPACT_LOWERS: float = 0.4

# Composite score (0–100) → risk level, inclusive lower bounds.
RISK_LEVEL_THRESHOLDS: tuple[tuple[str, float], ...] = (
    ("critical", 80.0),
    ("high", 60.0),
    ("moderate", 35.0),
)


# ── Profile helpers ────────────────────────────────────────────────────────


def _ramp_up(value: float, lo: float, hi: float) -> float:
    """0 below ``lo``, 1 at/above ``hi``, linear between."""
    if value <= lo:
        return 0.0
    if value >= hi:
        return 1.0
    return (value - lo) / (hi - lo)


def _ramp_down(value: float, at: float, beyond: float) -> float:
    """1 below/at ``at``, 0 at/above ``beyond``, linear between."""
    if value <= at:
        return 1.0
    if value >= beyond:
        return 0.0
    return 1.0 - (value - at) / (beyond - at)


def _triangle(value: float, lo: float, peak_lo: float, peak_hi: float, hi: float) -> float:
    """0 outside [lo, hi], 1 across [peak_lo, peak_hi], linear ramps in between."""
    if value < lo or value > hi:
        return 0.0
    if value <= peak_lo:
        return 1.0 if peak_lo == lo else (value - lo) / (peak_lo - lo)
    if value <= peak_hi:
        return 1.0
    return 1.0 if peak_hi == hi else 1.0 - (value - peak_hi) / (hi - peak_hi)


def _temperature_favorability(band: tuple[float, float], temp: float) -> float:
    """1 inside the band, linearly fading to 0 a shoulder-width outside it."""
    lo, hi = band
    if temp < lo:
        return max(0.0, 1.0 - (lo - temp) / TEMP_SHOULDER_DEG)
    if temp > hi:
        return max(0.0, 1.0 - (temp - hi) / TEMP_SHOULDER_DEG)
    return 1.0


def _profile_value(profile: tuple, value: float) -> float:
    """Dispatch a favorability profile onto a single observed value."""
    kind = profile[0]
    if kind == "ramp_up":
        return _ramp_up(value, profile[1], profile[2])
    if kind == "ramp_down":
        return _ramp_down(value, profile[1], profile[2])
    if kind == "triangle":
        return _triangle(value, profile[1], profile[2], profile[3], profile[4])
    if kind == "flat":
        return profile[1]
    return 0.0


# ── Pathogen classification ────────────────────────────────────────────────


def pathogen_class(pathogen_type: str | None) -> str:
    """Normalize the catalog's free-text ``pathogen_type`` into a rule class.

    The catalog stores human labels like ``Fungus (Alternaria solani)`` or
    ``Virus (TYLCV)``; the engine keys its rules on the coarse class so a new
    disease needs no code change — only a recognizable label.
    """
    if not pathogen_type:
        return "unknown"
    text = pathogen_type.lower()
    if "virus" in text:
        return "viral"
    if "phytoplasma" in text:
        return "phytoplasma"
    if "bacteri" in text:
        return "bacterial"
    if "fung" in text or "oomycete" in text:
        return "fungal"
    return "unknown"


# ── Factor computation ─────────────────────────────────────────────────────


def _compute_factors(pclass: str, weather: WeatherData) -> list[dict[str, float | str]]:
    """Favorability + impact label for each weather factor under ``pclass``."""
    entries = [
        ("humidity", f"relative humidity {weather.humidity_percent:.0f}%",
         HUMIDITY_PROFILES[pclass], weather.humidity_percent),
        ("temperature", f"temperature {weather.temperature_c:.1f}°C",
         None, weather.temperature_c),
        ("rainfall", f"rainfall {weather.rainfall_mm:.1f} mm",
         RAINFALL_PROFILES[pclass], weather.rainfall_mm),
        ("wind", f"wind {weather.wind_speed_ms:.1f} m/s",
         WIND_PROFILES[pclass], weather.wind_speed_ms),
    ]
    factors: list[dict[str, float | str]] = []
    for factor, condition, profile, value in entries:
        contribution = (
            _temperature_favorability(TEMPERATURE_BANDS[pclass], float(value))
            if profile is None
            else _profile_value(profile, float(value))
        )
        if contribution >= IMPACT_RAISES:
            impact = "raises"
        elif contribution <= IMPACT_LOWERS:
            impact = "lowers"
        else:
            impact = "neutral"
        factors.append(
            {
                "factor": factor,
                "condition": condition,
                "contribution": round(contribution, 3),
                "impact": impact,
            }
        )
    return factors


def _risk_level(score: float) -> str:
    """Map a 0–100 composite score to a risk level (inclusive lower bounds)."""
    for level, threshold in RISK_LEVEL_THRESHOLDS:
        if score >= threshold:
            return level
    return "low"


def _explain(pclass: str, factors: list[dict[str, float | str]]) -> str:
    """Plain-language summary listing the conditions that drive risk up."""
    drivers = [str(f["condition"]) for f in factors if float(f["contribution"]) >= IMPACT_RAISES]
    if drivers:
        return f"{', '.join(drivers)} favor {pclass} disease conditions."
    return f"Current weather is not especially favorable for {pclass} disease conditions."


class DiseaseRiskService:
    """Rule-based disease-risk assessment against current weather."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def assess_crop(
        self, crop_id: int, weather: WeatherData, *, is_fallback: bool = False
    ) -> WeatherRiskOut:
        """Score every catalog disease of ``crop_id`` against ``weather``.

        Raises :class:`CropNotFoundError` (404) when the crop is unsupported.
        """
        crop = await self._load_crop(crop_id)
        risks = [self.assess(disease, weather) for disease in crop.diseases]
        risks.sort(key=lambda risk: risk.risk_score, reverse=True)
        return WeatherRiskOut(
            crop=CropOut.model_validate(crop),
            weather=weather_to_out(weather, is_fallback=is_fallback),
            risks=risks,
            evaluated_at=datetime.now(UTC),
        )

    @staticmethod
    def assess(disease: Disease, weather: WeatherData) -> DiseaseRiskOut:
        """Pure per-disease assessment — no DB access, fully deterministic.

        Kept static so tests can drive any disease × weather scenario (and any
        risk level) without seeding rows, while ``assess_crop`` stays a thin
        catalog lookup around it.
        """
        pclass = pathogen_class(disease.pathogen_type)
        factors = _compute_factors(pclass, weather)
        score = round(
            100.0
            * sum(float(f["contribution"]) * FACTOR_WEIGHTS[str(f["factor"])] for f in factors),
            1,
        )
        return DiseaseRiskOut(
            disease_id=disease.id,
            disease_name=disease.name,
            pathogen_type=disease.pathogen_type,
            risk_level=_risk_level(score),
            risk_score=score,
            factors=[RiskFactorOut(**f) for f in factors],
            explanation=_explain(pclass, factors),
        )

    async def _load_crop(self, crop_id: int) -> Crop:
        crop = await self.db.scalar(
            select(Crop).options(selectinload(Crop.diseases)).where(Crop.id == crop_id)
        )
        if crop is None:
            raise CropNotFoundError(
                f"Crop {crop_id} is not in the catalog (unsupported crop)."
            )
        return crop
