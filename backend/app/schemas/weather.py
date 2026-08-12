"""Weather + disease-risk schemas (M5, Task 1).

Response DTOs for ``/weather/current`` and ``/weather/risk``. The weather
payload is the *normalized* application schema — every upstream provider
(OpenWeather, the deterministic mock, or a future source) is mapped into these
fields by :class:`app.services.weather.WeatherService`, so clients never see a
provider-specific shape.

The disease-risk payload is self-contained: the crop, the weather it was
evaluated against, a ranked list of per-disease risk assessments (level, score,
driving factors, explanation) and the evaluation timestamp.
"""

from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.catalog import CropOut

# Canonical risk levels (ascending severity). Mirrored by the service policy
# thresholds in ``app.services.weather_risk``.
RISK_LEVELS = ("low", "moderate", "high", "critical")


class WeatherLocationOut(BaseModel):
    """The coordinates a weather reading (or risk assessment) is for."""

    lat: float = Field(description="Latitude (WGS84, -90…90)")
    lng: float = Field(description="Longitude (WGS84, -180…180)")


class WeatherOut(BaseModel):
    """Normalized current weather for one location (provider-independent)."""

    temperature_c: float = Field(description="Air temperature in °C")
    humidity_percent: float = Field(
        ge=0.0, le=100.0, description="Relative humidity (0–100%)"
    )
    rainfall_mm: float = Field(ge=0.0, description="Precipitation in the window (mm; 0 when n/a)")
    wind_speed_ms: float = Field(ge=0.0, description="Wind speed in m/s")
    wind_direction_deg: float | None = Field(
        default=None, description="Wind direction in degrees (0–360); null when unknown"
    )
    condition: str = Field(description="Human-readable condition, e.g. 'Clear', 'Rain'")
    observed_at: datetime = Field(description="When the observation was taken (UTC)")
    location: WeatherLocationOut
    provider: str = Field(description="Which source supplied the data (e.g. 'mock', 'openweather')")
    is_fallback: bool = Field(
        default=False,
        description="True when the configured live source failed and the mock was used",
    )


class RiskFactorOut(BaseModel):
    """One weather factor's contribution to a disease's risk score.

    ``contribution`` is the factor's favorability for the pathogen class in
    [0, 1] before weighting; ``impact`` labels whether the observed condition
    raises, lowers, or is neutral for that pathogen.
    """

    factor: str = Field(description="humidity | temperature | rainfall | wind")
    condition: str = Field(
        description="Human-readable observed value, e.g. 'relative humidity 88%'"
    )
    contribution: float = Field(
        ge=0.0, le=1.0, description="Favorability of this condition for the pathogen (0–1)"
    )
    impact: str = Field(description="raises | lowers | neutral")


class DiseaseRiskOut(BaseModel):
    """Disease-risk assessment for one catalog disease under current weather."""

    disease_id: int
    disease_name: str
    pathogen_type: str | None = Field(
        default=None,
        description="Pathogen label from the catalog (e.g. 'Fungus (Alternaria solani)')",
    )
    risk_level: str = Field(description="low | moderate | high | critical")
    risk_score: float = Field(
        ge=0.0, le=100.0, description="Composite weather-risk score (0–100)"
    )
    factors: list[RiskFactorOut] = Field(default_factory=list)
    explanation: str = Field(description="Plain-language summary of the driving factors")


class WeatherRiskOut(BaseModel):
    """GET /weather/risk — per-crop disease risk under current weather.

    ``risks`` covers every disease the catalog knows for the crop, ranked by
    ``risk_score`` descending so the top entry is the most at-risk disease.
    """

    crop: CropOut
    weather: WeatherOut = Field(description="The weather the risks were evaluated against")
    risks: list[DiseaseRiskOut] = Field(default_factory=list)
    evaluated_at: datetime = Field(description="When the assessment was computed (UTC)")
