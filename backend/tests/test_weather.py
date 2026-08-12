"""M5, Task 1 tests — weather provider abstraction + disease-risk engine.

Covers the provider interface (protocol shape), the deterministic mock source,
normalization into the app's weather schema, live-provider failures (timeout /
HTTP / malformed / missing) plus service-level fallback, the rule-based risk
engine across all four risk levels with pinned scores, invalid inputs,
unsupported crops, authenticated access, and OpenAPI regression.
"""

from datetime import UTC, datetime

import httpx
import pytest
from sqlalchemy import select

from app.db.seed import seed_catalog
from app.db.session import async_session_factory
from app.main import app
from app.models.catalog import Crop, Disease
from app.schemas.weather import RISK_LEVELS
from app.services.weather import (
    InvalidLocationError,
    MockWeatherProvider,
    OpenWeatherProvider,
    WeatherApiError,
    WeatherData,
    WeatherDataMissingError,
    WeatherLocation,
    WeatherMalformedResponseError,
    WeatherProviderError,
    WeatherService,
    WeatherTimeoutError,
    weather_to_out,
)
from app.services.weather_risk import CropNotFoundError, DiseaseRiskService, pathogen_class


# ── Helpers ────────────────────────────────────────────────────────────────


def _weather(**overrides) -> WeatherData:
    """A normalized WeatherData with sensible defaults, overrideable per test."""
    base: dict = {
        "temperature_c": 26.0,
        "humidity_percent": 70.0,
        "rainfall_mm": 0.0,
        "wind_speed_ms": 2.0,
        "wind_direction_deg": 180.0,
        "condition": "clear",
        "observed_at": datetime.now(UTC),
        "location": WeatherLocation(lat=10.0, lng=77.0),
        "provider": "mock",
    }
    base.update(overrides)
    return WeatherData(**base)


async def _register(client, phone: str) -> dict:
    resp = await client.post(
        "/api/v1/auth/register",
        json={"phone": phone, "name": "Tester", "role": "farmer", "password": "secret123"},
    )
    assert resp.status_code == 201, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


async def _seed_catalog_only():
    async with async_session_factory() as db:
        await seed_catalog(db)


async def _tomato_id() -> int:
    async with async_session_factory() as db:
        crop = await db.scalar(select(Crop).where(Crop.name == "tomato"))
        assert crop is not None
        return crop.id


def _openweather_payload(
    temp: float = 26.0,
    humidity: float = 70.0,
    rain: float | None = None,
    wind_speed: float = 2.0,
    wind_deg: float = 180.0,
    condition: str = "Clear",
) -> dict:
    payload = {
        "coord": {"lat": 10.0, "lon": 77.0},
        "weather": [{"id": 800, "main": condition, "description": "clear sky", "icon": "01d"}],
        "main": {"temp": temp, "feels_like": temp, "humidity": humidity},
        "wind": {"speed": wind_speed, "deg": wind_deg},
        "dt": 1_700_000_000,
        "name": "Test",
    }
    if rain is not None:
        payload["rain"] = {"1h": rain}
    return payload


def _fungal_disease() -> Disease:
    return Disease(
        id=1, crop_id=1, name="Early Blight", pathogen_type="Fungus (Alternaria solani)"
    )


# ── Provider interface & normalized schema ────────────────────────────────


async def test_weather_service_accepts_any_provider_implementation():
    """The provider interface is structural: any object with ``name``+``current`` works."""

    class CustomProvider:
        name = "custom"

        async def current(self, lat: float, lng: float) -> WeatherData:
            return _weather(provider="custom")

    result = await WeatherService(provider=CustomProvider()).get_current(10.0, 77.0)
    assert result.data.provider == "custom"
    assert result.is_fallback is False


async def test_mock_provider_is_deterministic():
    first = await MockWeatherProvider().current(10.0, 77.0)
    second = await MockWeatherProvider().current(10.0, 77.0)
    for field in (
        "temperature_c",
        "humidity_percent",
        "rainfall_mm",
        "wind_speed_ms",
        "wind_direction_deg",
        "condition",
    ):
        assert getattr(first, field) == getattr(second, field)
    # Different locations are allowed to differ (still no randomness involved).
    other = await MockWeatherProvider().current(20.0, 90.0)
    assert other.location.lat == 20.0 and other.location.lng == 90.0
    assert 0.0 <= other.humidity_percent <= 100.0


async def test_mock_provider_overrides_force_a_scenario():
    data = await MockWeatherProvider(
        temperature_c=32.0, humidity_percent=95.0, rainfall_mm=6.0, wind_speed_ms=0.5,
        condition="rain",
    ).current(10.0, 77.0)
    assert data.temperature_c == 32.0
    assert data.humidity_percent == 95.0
    assert data.rainfall_mm == 6.0
    assert data.wind_speed_ms == 0.5
    assert data.condition == "rain"


async def test_weather_to_out_normalizes_response_schema():
    data = _weather(temperature_c=28.5, humidity_percent=80.0, rainfall_mm=2.0)
    out = weather_to_out(data, is_fallback=False)
    assert out.temperature_c == 28.5
    assert out.humidity_percent == 80.0
    assert out.rainfall_mm == 2.0
    assert out.location.lat == 10.0 and out.location.lng == 77.0
    assert out.provider == "mock"
    assert out.is_fallback is False
    # Observed timestamps serialize timezone-aware (UTC).
    assert out.observed_at.tzinfo is not None


# ── OpenWeather live provider ──────────────────────────────────────────────


async def test_openweather_provider_normalizes_payload():
    transport = httpx.MockTransport(
        lambda request: httpx.Response(
            200, json=_openweather_payload(temp=28.5, humidity=80.0, rain=2.0, wind_speed=3.2)
        )
    )
    provider = OpenWeatherProvider("k", timeout_seconds=2.0, transport=transport)
    data = await provider.current(10.0, 77.0)
    assert data.provider == "openweather"
    assert data.temperature_c == 28.5
    assert data.humidity_percent == 80.0
    assert data.rainfall_mm == 2.0
    assert data.wind_speed_ms == 3.2
    assert data.wind_direction_deg == 180.0
    assert data.condition == "Clear"
    assert data.location.lat == 10.0 and data.location.lng == 77.0
    assert data.observed_at.tzinfo is not None


async def test_openweather_http_error_raises_typed_api_error():
    transport = httpx.MockTransport(lambda request: httpx.Response(401, json={"message": "no"}))
    provider = OpenWeatherProvider("bad", timeout_seconds=2.0, transport=transport)
    with pytest.raises(WeatherApiError) as exc:
        await provider.current(10.0, 77.0)
    assert "401" in str(exc.value)


async def test_openweather_timeout_raises_typed_error():
    def _timeout(_request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectTimeout("connection timed out")

    transport = httpx.MockTransport(_timeout)
    provider = OpenWeatherProvider("k", timeout_seconds=0.01, transport=transport)
    with pytest.raises(WeatherTimeoutError):
        await provider.current(10.0, 77.0)


async def test_openweather_malformed_json_raises_typed_error():
    transport = httpx.MockTransport(lambda request: httpx.Response(200, content=b"<html>nope</html>"))
    provider = OpenWeatherProvider("k", timeout_seconds=2.0, transport=transport)
    with pytest.raises(WeatherMalformedResponseError):
        await provider.current(10.0, 77.0)


async def test_openweather_missing_fields_raises_typed_error():
    payload = {"coord": {"lat": 10.0, "lon": 77.0}, "dt": 1_700_000_000}
    transport = httpx.MockTransport(lambda request: httpx.Response(200, json=payload))
    provider = OpenWeatherProvider("k", timeout_seconds=2.0, transport=transport)
    with pytest.raises(WeatherDataMissingError):
        await provider.current(10.0, 77.0)


async def test_openweather_non_numeric_temp_raises_typed_error():
    payload = {"main": {"temp": "hot", "humidity": 70}, "dt": 1_700_000_000}
    transport = httpx.MockTransport(lambda request: httpx.Response(200, json=payload))
    provider = OpenWeatherProvider("k", timeout_seconds=2.0, transport=transport)
    with pytest.raises(WeatherMalformedResponseError):
        await provider.current(10.0, 77.0)


# ── Service fallback & validation ──────────────────────────────────────────


class _FailingProvider:
    name = "failing"

    async def current(self, lat: float, lng: float) -> WeatherData:
        raise WeatherProviderError("boom")


async def test_service_falls_back_to_mock_on_provider_failure():
    service = WeatherService(provider=_FailingProvider(), fallback_enabled=True)
    result = await service.get_current(10.0, 77.0)
    assert result.is_fallback is True
    assert result.data.provider == "mock"


async def test_service_raises_when_fallback_disabled():
    service = WeatherService(provider=_FailingProvider(), fallback_enabled=False)
    with pytest.raises(WeatherProviderError):
        await service.get_current(10.0, 77.0)


async def test_service_healthy_provider_no_fallback():
    result = await WeatherService(provider=MockWeatherProvider(), fallback_enabled=True).get_current(
        10.0, 77.0
    )
    assert result.is_fallback is False
    assert result.data.provider == "mock"


async def test_service_rejects_invalid_location():
    service = WeatherService()
    with pytest.raises(InvalidLocationError):
        await service.get_current(91.0, 0.0)
    with pytest.raises(InvalidLocationError):
        await service.get_current(0.0, -181.0)


# ── Disease-risk engine: pathogen classes & levels ─────────────────────────


async def test_pathogen_class_parses_catalog_labels():
    assert pathogen_class("Fungus (Alternaria solani)") == "fungal"
    assert pathogen_class("Oomycete (Phytophthora infestans)") == "fungal"
    assert pathogen_class("Bacterium (Xanthomonas oryzae pv. oryzae)") == "bacterial"
    assert pathogen_class("Virus (Tomato yellow leaf curl virus, TYLCV)") == "viral"
    assert pathogen_class("Phytoplasma") == "phytoplasma"
    assert pathogen_class(None) == "unknown"


async def test_risk_is_provider_independent():
    """The engine keys on weather values only — the provider name must not matter."""
    from_mock = DiseaseRiskService.assess(_fungal_disease(), _weather(provider="mock"))
    from_live = DiseaseRiskService.assess(_fungal_disease(), _weather(provider="openweather"))
    assert from_mock.risk_score == from_live.risk_score
    assert from_mock.risk_level == from_live.risk_level
    assert from_mock.factors == from_live.factors


async def test_fungal_critical_in_warm_humid_still_weather():
    out = DiseaseRiskService.assess(
        _fungal_disease(),
        _weather(temperature_c=26.0, humidity_percent=90.0, rainfall_mm=2.0, wind_speed_ms=0.8),
    )
    assert out.risk_score == 88.0
    assert out.risk_level == "critical"
    assert out.pathogen_type == "Fungus (Alternaria solani)"
    humidity = next(f for f in out.factors if f.factor == "humidity")
    assert humidity.impact == "raises"
    assert humidity.contribution == 1.0
    assert "relative humidity" in humidity.condition
    assert "favor" in out.explanation


async def test_fungal_high_risk_around_middle_thresholds():
    out = DiseaseRiskService.assess(
        _fungal_disease(),
        _weather(temperature_c=24.0, humidity_percent=80.0, rainfall_mm=3.0, wind_speed_ms=4.0),
    )
    assert out.risk_score == 77.2
    assert out.risk_level == "high"


async def test_fungal_moderate_risk_in_mixed_weather():
    out = DiseaseRiskService.assess(
        _fungal_disease(),
        _weather(temperature_c=24.0, humidity_percent=70.0, rainfall_mm=0.0, wind_speed_ms=3.0),
    )
    assert out.risk_score == 56.5
    assert out.risk_level == "moderate"


async def test_fungal_low_risk_in_cool_dry_windy_weather():
    out = DiseaseRiskService.assess(
        _fungal_disease(),
        _weather(temperature_c=12.0, humidity_percent=40.0, rainfall_mm=0.0, wind_speed_ms=7.0),
    )
    assert out.risk_score == 0.0
    assert out.risk_level == "low"
    assert "not especially favorable" in out.explanation


async def test_viral_risk_peaks_at_mid_humidity_light_wind():
    disease = Disease(id=2, crop_id=1, name="Leaf Curl", pathogen_type="Virus (TYLCV)")
    out = DiseaseRiskService.assess(
        disease,
        _weather(temperature_c=28.0, humidity_percent=60.0, rainfall_mm=0.0, wind_speed_ms=1.0),
    )
    assert out.risk_score == 100.0
    assert out.risk_level == "critical"


async def test_risk_level_threshold_boundaries():
    """Score 80 → critical, 60 → high, 35 → moderate, just-below → previous.

    Fungal: score = 100·(0.35·h + 0.30·t + 0.20·r + 0.15·w). Fixing t = 1.0
    (24 °C, in band) and r = 0 (no rain) leaves humidity h and wind w to drive
    the exact boundary scores.
    """
    disease = _fungal_disease()

    critical = DiseaseRiskService.assess(
        disease,
        _weather(temperature_c=24.0, humidity_percent=85.0, rainfall_mm=0.0, wind_speed_ms=0.5),
    )
    # 35·1.0 + 30·1.0 + 15·1.0 = 80.0
    assert critical.risk_score == 80.0
    assert critical.risk_level == "critical"

    high = DiseaseRiskService.assess(
        disease,
        _weather(temperature_c=24.0, humidity_percent=67.86, rainfall_mm=0.0, wind_speed_ms=0.5),
    )
    # 35·0.429 + 30 + 15 ≈ 60.0
    assert high.risk_score == 60.0
    assert high.risk_level == "high"

    moderate = DiseaseRiskService.assess(
        disease,
        _weather(temperature_c=24.0, humidity_percent=58.0, rainfall_mm=0.0, wind_speed_ms=5.5),
    )
    # 35·0.1 + 30 + 15·0.1 = 35.0
    assert moderate.risk_score == 35.0
    assert moderate.risk_level == "moderate"

    low = DiseaseRiskService.assess(
        disease,
        _weather(temperature_c=24.0, humidity_percent=55.0, rainfall_mm=0.0, wind_speed_ms=6.0),
    )
    # 30 + 0 + 0 = 30.0 → below the moderate floor
    assert low.risk_score == 30.0
    assert low.risk_level == "low"


# ── /weather endpoints (auth, validation, unsupported crop) ────────────────


async def test_weather_endpoints_require_auth(client):
    assert (await client.get("/api/v1/weather/current?lat=10.0&lng=77.0")).status_code == 401
    assert (await client.get("/api/v1/weather/risk?crop_id=1&lat=10.0&lng=77.0")).status_code == 401


async def test_current_weather_endpoint_happy_path(client):
    headers = await _register(client, "+919000000301")
    resp = await client.get("/api/v1/weather/current?lat=10.0&lng=77.0", headers=headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["provider"] == "mock"
    assert body["is_fallback"] is False
    assert 0.0 <= body["humidity_percent"] <= 100.0
    assert -90.0 <= body["location"]["lat"] <= 90.0
    assert body["observed_at"]


async def test_current_weather_out_of_range_coordinates_rejected(client):
    headers = await _register(client, "+919000000302")
    resp = await client.get("/api/v1/weather/current?lat=200.0&lng=77.0", headers=headers)
    assert resp.status_code == 422


async def test_disease_risk_endpoint_happy_path(client):
    await _seed_catalog_only()
    crop_id = await _tomato_id()
    headers = await _register(client, "+919000000303")
    resp = await client.get(
        f"/api/v1/weather/risk?crop_id={crop_id}&lat=10.0&lng=77.0", headers=headers
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["crop"]["name"] == "tomato"
    assert body["evaluated_at"]
    assert body["weather"]["provider"] == "mock"
    assert body["risks"]  # the catalog knows ≥1 disease for tomato
    scores = [risk["risk_score"] for risk in body["risks"]]
    assert scores == sorted(scores, reverse=True)  # ranked highest first
    for risk in body["risks"]:
        assert risk["risk_level"] in RISK_LEVELS
        assert 0.0 <= risk["risk_score"] <= 100.0
        assert risk["factors"] and risk["explanation"]


async def test_disease_risk_unsupported_crop_returns_404(client):
    await _seed_catalog_only()
    headers = await _register(client, "+919000000304")
    resp = await client.get(
        "/api/v1/weather/risk?crop_id=999999&lat=10.0&lng=77.0", headers=headers
    )
    assert resp.status_code == 404
    assert "not in the catalog" in resp.json()["error"]["message"].lower()


async def test_disease_risk_service_raises_for_unsupported_crop():
    await _seed_catalog_only()
    async with async_session_factory() as db:
        service = DiseaseRiskService(db)
        with pytest.raises(CropNotFoundError):
            await service.assess_crop(999999, _weather())


# ── Regression ─────────────────────────────────────────────────────────────


async def test_openapi_exposes_weather_endpoints():
    paths = app.openapi()["paths"]
    assert "/api/v1/weather/current" in paths
    assert "/api/v1/weather/risk" in paths
    # Both are GET and authenticated (no public exposure).
    assert "get" in paths["/api/v1/weather/current"]
    assert "get" in paths["/api/v1/weather/risk"]
