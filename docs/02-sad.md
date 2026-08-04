# Software Architecture Document — NeuroPlant AI

**Version:** 1.0 · **Date:** 2026-08-04 · **Status:** Approved

Companion to the architecture plan (`plan: gleaming-plotting-quill.md`). This
document expands the component model, layering, extensibility seams, and key
decisions. The canonical diagrams live in `docs/03-er-diagram.md`,
`docs/04-sequence-diagrams.md`, `docs/06-deployment.md`, `docs/08-ai-pipeline.md`.

## 1. Architectural Style

**Modular monolith, offline-first web app.**

- One FastAPI deployable containing cleanly-bounded domain modules, with an
  **event outbox** so any module can publish facts that other modules consume
  without compile-time coupling. Services are **extractable** to microservices
  later (payments, marketplace) with zero producer changes.
- The client is a **PWA** that treats the server as a sync endpoint rather than
  a live dependency: local-first storage, offline queues, on-device inference.
- Everything behind **interfaces** (`StorageService`, `SpeechService`,
  `TranslationService`, `PaymentGateway`, `DeliveryPartner`, `DiseaseClassifier`,
  `AnalysisProvider`, `TelemetryIngestor`) → providers are swappable by config.

## 2. Component Model

### 2.1 Frontend (React 19 + Vite + TS + Tailwind v4 + shadcn/ui)
```
src/
├── app/          providers (theme, i18n, query, socket), router, error boundaries
├── offline/      service worker, IndexedDB repository, sync engine, TF.js inference
├── features/     one domain folder: auth, detection, cropDoctor, assistant, voice,
│                 weather, outbreaks, soil, calendar, yield, prices, finance,
│                 marketplace, store, community, experts, analytics, admin, settings
├── lib/          API client (typed, auth-aware, offline-aware), utils, i18n
├── stores/       Zustand (auth/session, language, voice, offline status)
└── components/   ui (shadcn) + shared (voice bar, heatmap, charts, cards)
```
Key decision: **the API client intercepts network failures and enqueues
mutations** into IndexedDB; reads prefer cache-then-server. The service worker
serves the app shell + cached GET catalog data instantly on reload.

### 2.2 Backend (FastAPI, layered)
```
api/v1 routers  →  services (domain logic + event publishers)  →  repositories
                                  │
   ┌────────────┬─────────────────┼──────────────────┬───────────────────┐
 services: detection · treatment · cropDoctor · assistant · soil · calendar ·
 yield · weather · outbreaks · prices · payments · notifications · finance ·
 dataset · storage
   └────────────┴─────────────────┼──────────────────┴───────────────────┘
                    workers (Celery) · ws (WebSocket) · integrations
```
- **Routers**: validation + serialization only (Pydantic). No business logic.
- **Services**: transactional domain logic; publish domain events to the outbox.
- **Repositories**: data access; domain models never leak SQL.
- **Workers**: long-running/async (inference, PDF, notifications, retraining).

### 2.3 Data
PostgreSQL (prod) / SQLite (native dev) via SQLAlchemy 2.0 async + Alembic.
Redis: Celery broker/result, cache, rate-limit, WS pub/sub. Object storage:
S3-compatible (R2/Cloudflare in prod, MinIO locally) for images, heatmaps, PDFs,
model artifacts.

### 2.4 Event outbox
`outbox_events(id, topic, payload, status, attempts, created_at)`. A publisher
writes within the business transaction; a Celery dispatcher delivers to
subscribers (notifications, analytics, dataset ingestion, outbreak alerts).
Swap to Redis Streams/Kafka = only the dispatcher changes.

## 3. Extensibility Seams (future-proofing)

| Seam | Contract | Enables |
|---|---|---|
| `MediaItem` | `{source_type, url, lat/lng, captured_at, crop_id, part_type}` | drone/satellite/IoT camera = new ingestion adapter |
| `AnalysisProvider` | `analyze(MediaItem|features) → AnalysisResult` | pest AI, deficiency AI, yield AI as new providers |
| `TelemetryIngestor` | normalize sensor streams → `telemetry` table | IoT, smart-irrigation controllers |
| Model registry | `model_versions` + inference-by-capability | model swap without code change |
| API contract | versioned REST + WS, JWT | Android/iOS re-use same contracts |

## 4. Key Design Decisions

| Decision | Rationale |
|---|---|
| Modular monolith (not microservices now) | Team of one; deployable in weeks; outbox + seams preserve the microservice exit ramp |
| Offline-first PWA | Core value (detection) must work in low-connectivity fields |
| Hybrid AI serving | Self-hosted TF primary (no per-call cost, privacy); cloud fallback below confidence threshold |
| Hybrid voice | Web Speech free for en/hi; Google Cloud for full 12-language fidelity; degrade gracefully |
| SQLite dev fallback | Zero-dependency local development on machines without Docker/Postgres |
| Razorpay | UPI-first, marketplace payouts, India-standard |
| PaaS (Railway/Render) | Managed Postgres/Redis + worker support; cheapest ops for v1 |

## 5. Cross-Cutting Concerns

- **Security**: JWT rotation, MFA (TOTP), devices, login history, RBAC, argon2,
  rate limiting, image validation, Razorpay webhook signature verification,
  audit logs. (Full detail: `docs/10-risk-analysis.md` §security.)
- **Observability**: structlog (JSON in prod), `GET /health` + `GET /ready`,
  Sentry (M11), structured request IDs.
- **Error handling**: typed API envelope `{data|error, meta}`; idempotency keys
  on scans/orders/payouts; retries via tenacity.
- **Configuration**: 12-factor; `Settings` (pydantic-settings); env templates in
  `docker/.env.example`.

## 6. Data Flow (summary)

```
[Client uploads leaf image]
   → POST /api/v1/scans (client_scan_id, part_type)
   → validation (image magic bytes, size, type)
   → storage (S3/R2) → MediaItem
   → DiseaseClassifier.predict() [local TF; cloud fallback < 0.6]
   → severity/stage heuristics + Grad-CAM heatmap + plain-language explanation
   → disease record persisted → Crop Doctor series updated (if in series)
   → outbox events: scan.completed → notifications/analytics
   → response {disease, confidence, severity, stage, symptoms, heatmap_url, explanation}
```
See `docs/04-sequence-diagrams.md` for the detailed flows.
