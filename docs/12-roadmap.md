# Future Roadmap — NeuroPlant AI

The v1 architecture is deliberately built with extensibility seams so these
initiatives land as **new adapters, providers, or ingesters** — not core
rewrites. Each roadmap item names the seam it plugs into.

## Horizon 1 — data depth (post-launch, 0–6 mo)

| Item | Seam | Notes |
|---|---|---|
| More crops & diseases | catalog + dataset platform | label→retrain loop already ships; grow coverage by state/season |
| Better field-condition accuracy | dataset platform + eval gate | collect real-field images via app + experts |
| Fertilizer recommendation AI | `AnalysisProvider` (`DeficiencyAnalyzer`) | soil + crop + calendar → NPK plan; extend `soil_deficiency_predictions` |
| Pest detection AI | `AnalysisProvider` (`PestAnalyzer`) + catalog | reuses `MediaItem`, heatmap explainer, treatments |
| Price prediction v2 | `price_predictions` model registry | historical + weather + demand features |

## Horizon 2 — sensing & telemetry (6–18 mo)

| Item | Seam | Notes |
|---|---|---|
| **IoT sensors** (soil moisture, temp, humidity) | `TelemetryIngestor` → `telemetry` table | drives calendar/watering/yield; per-device auth |
| **Smart irrigation controllers** | `TelemetryIngestor` + actuator adapter | read telemetry → schedule → actuate; MQTT/CoAP adapters |
| **Drone image analysis** | `MediaItem.source_type=drone` + `AnalysisProvider` | tiled ortho ingest → per-zone disease map → treat map |
| **Satellite imagery** (NDVI, crop health) | `MediaItem.source_type=satellite` | periodic pull → field-level health index; PostGIS likely added |
| Weather station integration | weather provider adapter | on-farm stations replace/augment OpenWeather |

## Horizon 3 — platform & markets (12–24 mo)

| Item | Seam | Notes |
|---|---|---|
| **Mobile apps (Android/iOS)** | mobile-ready API + MFA + PWA | React Native or Flutter reuse versioned contracts; push via FCM/APNs |
| **Livestock management** | new domain module (models/services) | health, feed, weight tracking; extension of catalog + analytics |
| **Crop insurance / lending risk** | yield + soil + telemetry data | risk score API for partners |
| **Marketplace expansion** | payment/delivery adapters | multi-partner delivery, group-buying, B2B bulk orders |
| **Multi-region** (other states/countries) | i18n framework, crops catalog, schemes | language packs + regional seed data |
| **Cooperative/aggregator dashboards** | analytics module | village/aggregator rollups |

## Non-goals (explicitly deferred)

- Full KYC provider integration (manual verification remains).
- Real-time video analytics on drone streams (batch ingestion first).
- On-device full-catalog model (remains online; offline is reduced-class).
- Direct government data feeds (schemes are curated content).

## How the seams make this cheap

| Capability | Today (v1) | Horizon | Change needed |
|---|---|---|---|
| Disease AI | `DiseaseAnalyzer` | pest AI | new provider + label map; zero core change |
| Image sources | upload/camera | drone/satellite/IoT | new ingestion adapter (`source_type`); zero pipeline change |
| Sensor data | none (out of scope) | IoT/irrigation | `TelemetryIngestor` writes to `telemetry`; consumers already exist |
| Deploy | Railway/Render | scale-out | horizontal (stateless API + workers); outbox → Kafka swap optional |
| Clients | PWA | native apps | reuse API + auth; add push |

## Quarterly cadence

- **Q1**: launch (M11), data-depth push (accuracy, crops).
- **Q2**: pest AI + fertilizer AI; pilot weather-station integration.
- **Q3**: IoT + smart irrigation pilot; Android app beta.
- **Q4**: drone/satellite pilot with partner farms; livestock module decision.
