# M5 Task 1 — Weather & Disease-Risk Foundation — Completion Report

**Milestone:** M5 (Weather + Outbreaks + Yield + Prices + Maps), Task 1 of 6
**Scope:** Weather provider abstraction + rule-based disease-risk backend foundation
**Depends on:** M1 (auth/RBAC, `expert` role), M2 (crops/diseases catalog, `MediaItem`), M3 (soil/crop-plan context), M4 (none blocking)
**Baseline:** `v0.4.0-m4` (`c180f97`) — M4 complete, working tree clean
**Result:** 436 passed, 1 skipped (same baseline as M4); ruff lint/format, mypy, pip check all green. No existing gate weakened.

> **Out of scope (later M5 tasks):** notifications, outbreak dashboard, yield
> prediction, price dashboard, maps, frontend weather UI, push notifications.
> Those are explicitly deferred.

---

## 1. Architecture

```
app/core/config.py            # weather_provider, openweather_api_key,
                              #   weather_timeout_seconds, weather_fallback_enabled
app/services/weather.py       # WeatherProvider protocol + OpenWeather + Mock + WeatherService
app/services/weather_risk.py  # rule-based DiseaseRiskService (provider-independent)
app/schemas/weather.py        # WeatherOut, WeatherRiskOut, RiskFactorOut, …
app/api/v1/endpoints/weather.py  # GET /weather/current, GET /weather/risk
app/api/v1/router.py          # registers the weather router (M5 section)
app/main.py                   # exception handlers → 400/404/502 (no provider internals leak)
tests/test_weather.py         # 29 tests
```

The module follows the established milestone pattern: **catalog data in the DB,
rule *constants* in the service, no hardcoded advice in controllers.** The
disease-risk engine reuses the existing `crops`/`diseases` catalog and derives
its rules from each disease's `pathogen_type` — it does **not** duplicate any
disease definition.

---

## 2. Weather provider abstraction

A structural `Protocol` (`WeatherProvider`) defines the contract: a `name`
string plus `async current(lat, lng) -> WeatherData`. Any source can satisfy it
without subclassing.

| Provider | Source | Failure mode |
|---|---|---|
| `OpenWeatherProvider` | OpenWeatherMap Current Weather API (`units=metric`) | raises typed `WeatherProviderError` subtypes |
| `MockWeatherProvider` | deterministic, offline, coordinate-derived | never fails |

**Normalization.** Every source returns the app's own `WeatherData`
dataclass — never a provider-shaped payload. `WeatherService.get_current`
validates coordinates and applies the fallback policy:

```python
result = await WeatherService().get_current(lat, lng)
# result.data  -> WeatherData (normalized)
# result.is_fallback -> True when a live source failed and the mock was used
```

**Selection (settings-driven, no hardcoded secrets):**
- `weather_provider = "mock"` (default, zero-config dev) or `"openweather"`.
- `openweather_api_key` read from env (12-factor `.env`). When `openweather` is
  selected but the key is absent, the service logs a warning and falls back to
  the mock — it never crashes.

---

## 3. Normalized weather schema (`WeatherOut`)

Fields required by the M5 roadmap and surfaced to clients:

| Field | Notes |
|---|---|
| `temperature_c` | air temperature, °C |
| `humidity_percent` | relative humidity (0–100) |
| `rainfall_mm` | precipitation in the window (0 when not available) |
| `wind_speed_ms` | wind speed, m/s |
| `wind_direction_deg` | optional (null when unknown) |
| `condition` | human-readable, e.g. `"Clear"` / `"Rain"` |
| `observed_at` | UTC timestamp (timezone-aware) |
| `location` | `{lat, lng}` |
| `provider` | source identifier (`mock` / `openweather`) |
| `is_fallback` | `True` when degraded to the offline source |

---

## 4. Disease-risk rules (`app/services/weather_risk.py`)

**Provider-independent:** the engine consumes only `WeatherData`, so it behaves
identically whether the weather came from OpenWeather, the mock, or a future
regional provider.

**Pathogen classification.** The catalog's free-text `pathogen_type` is mapped
to a coarse rule class via `pathogen_class()`:
`Fungus`/`Oomycete` → `fungal`, `Bacterium` → `bacterial`, `Virus` → `viral`,
`Phytoplasma` → `phytoplasma`, else `unknown`. Adding a new disease needs no
code change — only a recognizable label in the seed catalog.

**Composite score (0–100).** Each of four weather factors is mapped to a
favorability in `[0, 1]` by a class-specific profile (ramp/triangle/temperature
band), then weighted and summed:

```
score = 100·(0.35·humidity + 0.30·temperature + 0.20·rainfall + 0.15·wind)
```

All weights, profile breakpoints, the temperature shoulder, the impact
thresholds (≥0.6 → `raises`, ≤0.4 → `lowers`), and the level bands are
**documented constants**, not magic numbers:

| Level | Score ≥ |
|---|---|
| critical | 80 |
| high | 60 |
| moderate | 35 |
| low | 0 |

**Response.** For each catalog disease of the crop the service returns
`disease_id`, `disease_name`, `pathogen_type`, `risk_level`, `risk_score`,
`factors` (per-factor `condition`/`contribution`/`impact`) and a plain-language
`explanation`. Risks are ranked by score descending so the top entry is the
most at-risk disease.

**No persistence.** The assessment is stateless over current weather — keeping
it free of any DB write. Historical weather (yield) and outbreak aggregation are
later M5 tasks that will reuse the same `WeatherData` seam.

---

## 5. API endpoints

Both endpoints are **authenticated (any role)**, mirroring the read-only
`/soil` and `/catalog` endpoints. Input is validated in three layers:
FastAPI `Query` range checks (422), the service's coordinate re-validation
(400), and catalog lookups (404).

| Method | Path | Description |
|---|---|---|
| GET | `/api/v1/weather/current?lat=&lng=` | normalized current weather for a location |
| GET | `/api/v1/weather/risk?crop_id=&lat=&lng=` | per-crop disease risk under current weather |

Example `/weather/risk` body:

```json
{
  "crop": {"id": 1, "name": "tomato", "common_name": "Tomato"},
  "weather": {"temperature_c": 28.5, "humidity_percent": 80.0, "rainfall_mm": 2.0,
              "wind_speed_ms": 3.2, "wind_direction_deg": 180.0, "condition": "Clear",
              "observed_at": "…", "location": {"lat": 10.0, "lng": 77.0},
              "provider": "mock", "is_fallback": false},
  "risks": [
    {"disease_id": 1, "disease_name": "Early Blight",
     "pathogen_type": "Fungus (Alternaria solani)", "risk_level": "high",
     "risk_score": 77.2, "factors": [ … ], "explanation": "…"},
    …
  ],
  "evaluated_at": "…"
}
```

---

## 6. Error handling (no provider internals leak)

Mapped in `app/main.py`:

| Condition | HTTP | Handler |
|---|---|---|
| invalid location (lat/lng out of range) | 400 | `InvalidLocationError` |
| unsupported crop (not in catalog) | 404 | `CropNotFoundError` |
| weather provider failure (timeout / HTTP / malformed / missing) | 502 | `WeatherProviderError` (+ typed subclasses) |

When the live provider fails **and** `weather_fallback_enabled` is `True`, the
service degrades to the mock and marks `is_fallback=True` rather than erroring.
The exception messages are generic ("The weather provider timed out.") so URLs,
API keys, and raw payloads never reach clients.

---

## 7. Tests (`tests/test_weather.py` — 29 tests)

| Area | Coverage |
|---|---|
| Provider interface | structural Protocol acceptance (custom provider resolves) |
| Mock provider | determinism, coordinate difference, scenario overrides |
| Normalized schema | `weather_to_out` maps every field, timezone-aware `observed_at` |
| OpenWeather | happy-path normalization; 401/timeout/malformed/missing-field/non-numeric errors |
| Service fallback | fallback on failure, raise when disabled, healthy path, invalid location |
| Disease-risk rules | pathogen-class parsing; provider-independence; **critical (88.0) / high (77.2) / moderate (56.5) / low (0.0)** with pinned scores; viral peak; threshold boundaries |
| Endpoints | auth required (401); happy paths; out-of-range 422; unsupported crop 404; ranking + score bounds |
| Regression | OpenAPI exposes both `/weather/*` GET routes |

Run with the rest of the suite (`pytest`): **436 passed, 1 skipped.**

---

## 8. Quality gates

| Gate | Command | Result |
|---|---|---|
| Lint | `ruff check .` | pass (only pre-existing M4 smoke-script findings, untouched) |
| Format | `ruff format --check .` | pass for all M5 files |
| Type | `mypy app` | pass |
| Tests | `pytest` | 436 passed, 1 skipped |
| Deps | `pip check` | No broken requirements found |

No existing gate was weakened; the pre-existing `scripts/m4_smoke_journey.py`
E501 findings are outside M5 scope and were not modified.

---

## 9. Known limitations

- **No DB tables added.** Weather observations and risk assessments are not
  persisted (by design — stateless over current weather). Historical storage
  arrives with yield prediction (Task 4).
- **Mock is the default source.** Native dev runs with `weather_provider=mock`;
  live OpenWeather requires `OPENWEATHER_API_KEY` and setting
  `weather_provider=openweather`. The OpenWeather adapter is fully implemented
  and unit-tested (transport injected), but only exercised against a real API
  when a key is present.
- **Conditions are point-in-time.** Risk reflects *current* weather only; no
  forecast blending, no multi-day accumulation (e.g. consecutive wet days).
- **Rules are heuristic, not trained.** Scores are explainable constants, the
  documented floor until ML arrives — consistent with the M3/M5 "rule-baseline
  floor until data accrues" principle.
- **No per-crop calibration.** All fungal crops share one profile; regional
  micro-climates are not modeled.

---

## 10. Future integration points

- **Notifications (Task 2):** `WeatherService.get_current` already exposes
  `is_fallback`; a scheduler can poll `/weather/risk` and emit alerts when a
  disease crosses a threshold — the `risk_level`/`risk_score` payload is the
  exact input.
- **Outbreak intelligence (Task 3):** `RiskFactorOut` factors + `risk_level`
  feed district heatmaps; expert verification reuses the M1 `expert` role.
- **Yield prediction (Task 4):** adds a historical `weather` table consumed by
  the same `WeatherData` seam; `DiseaseRiskService.assess` stays unchanged.
- **Maps / nearby (Task 6):** pairs `weather.location` with `crops`/farmers'
  geo already on the `User` model.
- **Live provider:** set `weather_provider=openweather` + key; optionally add a
  `WeatherProviderFactory` caching the selected instance (current code builds it
  per call, negligible cost at this scale).
