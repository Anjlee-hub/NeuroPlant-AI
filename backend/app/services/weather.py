"""Weather provider abstraction + normalized weather service (M5, Task 1).

Every weather source implements the :class:`WeatherProvider` protocol and
returns the app's *normalized* :class:`WeatherData` — never a provider-specific
payload. Two providers ship today:

* :class:`OpenWeatherProvider` — live data from the OpenWeatherMap Current
  Weather API (uses ``openweather_api_key`` + ``weather_timeout_seconds`` from
  settings). Every upstream failure (timeout, HTTP error, malformed JSON,
  missing fields) raises a typed :class:`WeatherProviderError` subclass so the
  caller can degrade gracefully without ever seeing raw upstream internals.
* :class:`MockWeatherProvider` — a deterministic, offline source for native
  dev and tests. Values are pure functions of the coordinates (no randomness),
  so the same location always yields the same weather; constructor overrides
  force a specific scenario.

:class:`WeatherService` selects the configured provider (``weather_provider``),
validates coordinates, and applies the fallback policy: when a live source
fails and ``weather_fallback_enabled`` is set, it degrades to the mock source
and marks the result ``is_fallback`` instead of erroring.

The risk engine (:mod:`app.services.weather_risk`) consumes only
:class:`WeatherData`, so it is provider-independent by construction.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Protocol

import httpx

from app.core.config import get_settings
from app.core.logging import get_logger
from app.schemas.weather import WeatherLocationOut, WeatherOut

logger = get_logger(__name__)


# ── Domain exceptions (mapped to HTTP in ``app.main``) ────────────────────


class InvalidLocationError(Exception):
    """Latitude/longitude outside valid ranges (lat -90…90, lng -180…180)."""


class WeatherProviderError(Exception):
    """Base class — an upstream weather source could not provide data.

    Subclasses carry the precise failure internally; the HTTP mapping surfaces
    a generic message so provider internals (URLs, keys, raw payloads) never
    leak to clients.
    """


class WeatherTimeoutError(WeatherProviderError):
    """The provider did not respond within the configured timeout."""


class WeatherApiError(WeatherProviderError):
    """The provider returned a non-success HTTP status (or is unreachable)."""


class WeatherMalformedResponseError(WeatherProviderError):
    """The provider response could not be parsed into weather fields."""


class WeatherDataMissingError(WeatherProviderError):
    """The provider response was valid but lacked required weather fields."""


# ── Normalized weather schema (provider-independent) ──────────────────────


@dataclass(frozen=True)
class WeatherLocation:
    """WGS84 coordinates for a weather observation."""

    lat: float
    lng: float


@dataclass(frozen=True)
class WeatherData:
    """The app's normalized weather record, regardless of source.

    Fields mirror the M5 roadmap needs: temperature, humidity, rainfall
    (precipitation where available), wind (speed + optional direction),
    a human-readable condition, the observation timestamp, and the location.
    """

    temperature_c: float
    humidity_percent: float
    rainfall_mm: float
    wind_speed_ms: float
    wind_direction_deg: float | None
    condition: str
    observed_at: datetime
    location: WeatherLocation
    provider: str


@dataclass(frozen=True)
class WeatherResult:
    """A weather fetch plus whether it degraded to the fallback source."""

    data: WeatherData
    is_fallback: bool = False


# ── Provider interface ─────────────────────────────────────────────────────


class WeatherProvider(Protocol):
    """Anything that can return normalized current weather for a location.

    Implementations set ``name`` (the source identifier surfaced to clients in
    ``WeatherOut.provider``) and implement :meth:`current`, which returns
    :class:`WeatherData` or raises a :class:`WeatherProviderError`.
    """

    name: str

    async def current(self, lat: float, lng: float) -> WeatherData: ...


# ── Live provider: OpenWeatherMap ──────────────────────────────────────────


class OpenWeatherProvider:
    """Current-weather data from the OpenWeatherMap API, normalized.

    All failures surface as typed :class:`WeatherProviderError` subclasses so
    the service can fall back (or the API can respond 502) without leaking the
    upstream URL, the API key, or the raw payload.
    """

    BASE_URL = "https://api.openweathermap.org/data/2.5/weather"
    name = "openweather"

    def __init__(
        self,
        api_key: str,
        *,
        timeout_seconds: float = 5.0,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        """``transport`` is injected by tests to stub the HTTP layer."""
        self.api_key = api_key
        self.timeout_seconds = timeout_seconds
        self._transport = transport

    async def current(self, lat: float, lng: float) -> WeatherData:
        params: dict[str, str | int | float] = {
            "lat": lat,
            "lon": lng,
            "appid": self.api_key,
            "units": "metric",  # °C + m/s straight from the API
        }
        try:
            async with httpx.AsyncClient(
                timeout=self.timeout_seconds, transport=self._transport
            ) as client:
                response = await client.get(self.BASE_URL, params=params)
        except httpx.TimeoutException as exc:
            raise WeatherTimeoutError("The weather provider timed out.") from exc
        except httpx.HTTPError as exc:
            raise WeatherApiError("The weather provider is unreachable.") from exc

        if response.status_code != 200:
            raise WeatherApiError(
                f"The weather provider returned HTTP {response.status_code}."
            )

        try:
            payload = response.json()
        except ValueError as exc:
            raise WeatherMalformedResponseError(
                "The weather provider returned malformed JSON."
            ) from exc
        return self._parse(payload, lat, lng)

    def _parse(self, payload: Any, lat: float, lng: float) -> WeatherData:
        """Map an OpenWeather current-weather payload into :class:`WeatherData`."""
        if not isinstance(payload, dict):
            raise WeatherMalformedResponseError(
                "The weather provider returned an unexpected shape."
            )

        main = payload.get("main")
        if not isinstance(main, dict):
            raise WeatherDataMissingError("The weather payload is missing 'main'.")

        temp = main.get("temp")
        humidity = main.get("humidity")
        if not isinstance(temp, (int, float)) or not isinstance(humidity, (int, float)):
            raise WeatherMalformedResponseError(
                "The weather payload has non-numeric temperature or humidity."
            )

        wind = payload.get("wind")
        if not isinstance(wind, dict):
            wind = {}
        wind_speed = wind.get("speed")
        wind_speed_ms = float(wind_speed) if isinstance(wind_speed, (int, float)) else 0.0
        wind_deg = wind.get("deg")
        wind_direction_deg = (
            float(wind_deg) if isinstance(wind_deg, (int, float)) else None
        )

        rain = payload.get("rain")
        if not isinstance(rain, dict):
            rain = {}
        rain_1h = rain.get("1h")
        rain_3h = rain.get("3h")
        if isinstance(rain_1h, (int, float)):
            rainfall_mm = float(rain_1h)
        elif isinstance(rain_3h, (int, float)):
            rainfall_mm = float(rain_3h)
        else:
            rainfall_mm = 0.0

        condition = "unknown"
        weather_list = payload.get("weather")
        if isinstance(weather_list, list) and weather_list and isinstance(weather_list[0], dict):
            condition = str(weather_list[0].get("main") or "unknown")

        dt = payload.get("dt")
        observed_at = (
            datetime.fromtimestamp(float(dt), tz=UTC)
            if isinstance(dt, (int, float))
            else datetime.now(UTC)
        )

        return WeatherData(
            temperature_c=float(temp),
            humidity_percent=float(humidity),
            rainfall_mm=rainfall_mm,
            wind_speed_ms=wind_speed_ms,
            wind_direction_deg=wind_direction_deg,
            condition=condition,
            observed_at=observed_at,
            location=WeatherLocation(lat=lat, lng=lng),
            provider=self.name,
        )


# ── Deterministic offline provider: mock ───────────────────────────────────


class MockWeatherProvider:
    """Deterministic, offline weather source for development and tests.

    Numeric values are pure functions of the coordinates — no randomness, no
    clock dependence — so the same location always yields the same weather and
    tests are stable across runs. Optional constructor overrides force a
    specific scenario (e.g. ``MockWeatherProvider(humidity_percent=95.0)``).
    """

    name = "mock"

    _FIELDS = (
        "temperature_c",
        "humidity_percent",
        "rainfall_mm",
        "wind_speed_ms",
        "wind_direction_deg",
        "condition",
    )

    def __init__(self, **overrides: float | str | None) -> None:
        self._overrides = {k: v for k, v in overrides.items() if k in self._FIELDS}

    async def current(self, lat: float, lng: float) -> WeatherData:
        # Tropical-band baseline that cools toward the poles, with a small
        # longitude wobble so nearby towns still differ.
        temperature = 28.0 - abs(lat) * 0.35 + (abs(lng) % 4.0) / 4.0
        humidity = 45.0 + (abs(lng * 1000) % 50)  # 45–94 %
        rainfall = 0.0
        if humidity >= 85.0:
            rainfall = round(humidity - 84.0, 1)  # 0–10 mm
        wind_speed = 0.5 + (abs(lat * 1000) % 55) / 10.0  # 0.5–6.0 m/s
        wind_direction = float(abs(lng * 1000) % 360)
        if rainfall > 0:
            condition = "rain"
        elif humidity >= 70:
            condition = "clouds"
        else:
            condition = "clear"

        values: dict[str, Any] = {
            "temperature_c": round(temperature, 2),
            "humidity_percent": round(humidity, 1),
            "rainfall_mm": rainfall,
            "wind_speed_ms": round(wind_speed, 2),
            "wind_direction_deg": wind_direction,
            "condition": condition,
        }
        values.update(self._overrides)

        return WeatherData(
            temperature_c=float(values["temperature_c"]),
            humidity_percent=float(values["humidity_percent"]),
            rainfall_mm=float(values["rainfall_mm"]),
            wind_speed_ms=float(values["wind_speed_ms"]),
            wind_direction_deg=(
                float(values["wind_direction_deg"])
                if values["wind_direction_deg"] is not None
                else None
            ),
            condition=str(values["condition"]),
            observed_at=datetime.now(UTC),
            location=WeatherLocation(lat=lat, lng=lng),
            provider=self.name,
        )


# ── Service: provider selection + fallback ─────────────────────────────────


class WeatherService:
    """Resolve the configured weather provider and validate coordinates.

    ``provider`` / ``fallback_enabled`` are injectable so tests can pin either
    (the endpoint defaults both from settings).
    """

    def __init__(
        self,
        provider: WeatherProvider | None = None,
        *,
        fallback_enabled: bool | None = None,
    ) -> None:
        self._provider = provider
        # None → read the setting at call time (tests pass an explicit value).
        self._fallback_enabled = fallback_enabled

    @staticmethod
    def _default_provider() -> WeatherProvider:
        """Provider chosen by ``weather_provider`` (mock when unconfigured)."""
        settings = get_settings()
        if settings.weather_provider == "openweather":
            if not settings.openweather_api_key:
                logger.warning(
                    "weather_openweather_not_configured",
                    hint="set OPENWEATHER_API_KEY or weather_provider=mock",
                )
                return MockWeatherProvider()
            return OpenWeatherProvider(
                api_key=settings.openweather_api_key,
                timeout_seconds=settings.weather_timeout_seconds,
            )
        return MockWeatherProvider()

    @staticmethod
    def _validate_location(lat: float, lng: float) -> None:
        if not -90.0 <= lat <= 90.0:
            raise InvalidLocationError("latitude must be between -90 and 90")
        if not -180.0 <= lng <= 180.0:
            raise InvalidLocationError("longitude must be between -180 and 180")

    async def get_current(self, lat: float, lng: float) -> WeatherResult:
        """Normalized current weather for a location, with fallback handling."""
        self._validate_location(lat, lng)

        provider = self._provider or self._default_provider()
        try:
            data = await provider.current(lat, lng)
            return WeatherResult(data=data, is_fallback=False)
        except WeatherProviderError:
            if self._fallback_enabled is None:
                fallback_enabled = get_settings().weather_fallback_enabled
            else:
                fallback_enabled = self._fallback_enabled
            if not fallback_enabled:
                raise
            logger.warning("weather_fallback", source=provider.name, lat=lat, lng=lng)
            data = await MockWeatherProvider().current(lat, lng)
            return WeatherResult(data=data, is_fallback=True)


def weather_to_out(data: WeatherData, *, is_fallback: bool) -> WeatherOut:
    """Normalized :class:`WeatherData` -> :class:`WeatherOut` response DTO."""
    return WeatherOut(
        temperature_c=data.temperature_c,
        humidity_percent=data.humidity_percent,
        rainfall_mm=data.rainfall_mm,
        wind_speed_ms=data.wind_speed_ms,
        wind_direction_deg=data.wind_direction_deg,
        condition=data.condition,
        observed_at=data.observed_at,
        location=WeatherLocationOut(lat=data.location.lat, lng=data.location.lng),
        provider=data.provider,
        is_fallback=is_fallback,
    )
