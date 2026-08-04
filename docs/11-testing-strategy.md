# Testing Strategy — NeuroPlant AI

## Principles

- **Test the behavior, not the implementation.** API-level tests via
  `httpx.AsyncClient` against the ASGI app; UI tests at the flow level.
- **Fast feedback** — unit tests in < 60s; integration vs real Postgres/Redis in
  CI (M2+); e2e isolated to critical journeys.
- **Every milestone ships green** — CI gates: `ruff` · `mypy` · `pytest` ·
  frontend `typecheck` + `build`.
- **AI tested as data** — model eval is a first-class CI job (accuracy, ECE,
  per-class), not a smoke assertion.

## Test pyramid

```
        ╱ e2e (Playwright) — critical journeys ╲        few
       ╱ integration (API ↔ PG/Redis/worker)   ╲
      ╱ unit (services, rules, helpers)          ╲      many
     ╱ static: ruff · mypy · tsc                   ╲
```

## Layers

### 1. Static analysis
- Backend: `ruff check`, `ruff format --check`, `mypy`.
- Frontend: `tsc -b --noEmit` (strict), ESLint.

### 2. Unit (backend `pytest`)
- Auth: hashing, token issue/refresh/rotation, RBAC, MFA TOTP, device revoke.
- Rules engines: severity/stage heuristics, soil deficiency, treatment
  selection, crop-calendar scheduling, crop-doctor score/trend/recovery.
- Offline sync: idempotent merge, conflict rules.
- Providers: each adapter with mocked external (Razorpay signature, weather
  mapping, speech/translation, delivery partners).
- DB-agnostic (SQLite via fixture) unless testing PG-specific behavior.

### 3. Integration (M2+)
- `testcontainers` Postgres + Redis; Alembic migrate up → exercise real flows.
- Scan pipeline: upload → validation → storage (MinIO/S3 stub) → classify
  (fixture model) → persist → explain.
- Marketplace order + Razorpay webhook → payout; payment idempotency.
- Outbreak: report → verify → heatmap + notification fan-out.
- Dataset: label → retrain (fixture) → eval gate → promote → serve.

### 4. AI evaluation (`ai/`)
- `eval.py` reports per-class accuracy, weighted top-1, **ECE** (calibration),
  confusion matrix on held-out split per model build.
- **Eval gate**: promotion blocked below thresholds (e.g. top-1 ≥ 0.90, ECE < 0.10).
- Grad-CAM sanity: heatmap non-trivial (activation variance), overlay valid.
- Offline (TF.js) parity: on-device top-5 matches server within tolerance on a
  golden set.

### 5. Frontend (Vitest + React Testing Library)
- Critical flows: auth, scan→result (incl. offline badge), calendar reminders,
  order placement, language/voice commands.
- Components: heatmap toggle, voice bar, charts, offline indicator.
- i18n: every locale loads; key parity enforced; RTL rendering for ur.

### 6. E2E (Playwright, M2+)
| Journey | Steps |
|---|---|
| Register → scan → result | register, upload leaf, assert diagnosis + heatmap, view history |
| Offline scan → sync | intercept network offline, scan, restore, assert synced |
| Marketplace order | browse → offer → checkout (sandbox) → tracking |
| Voice flow | tap mic → stub STT hi → assert navigation + TTS ack |
| Admin audit | admin action → assert audit-log entry |

## Offline & resilience tests
- Service worker: shell cache, catalog cache, sync queue drain, retry/backoff.
- Provider degrade: weather/LLM/GCP down → graceful degraded UX, no crash.

## Security tests
- Auth: token reuse after rotation, MFA bypass attempts, brute-force OTP lockout.
- Upload: magic-byte spoof rejection, oversized, EXIF strip, path traversal.
- RBAC: farmer vs expert vs admin route matrix.
- Rate limits trigger 429; Razorpay webhook bad signature → 400, no side effect.

## Coverage targets
- Backend unit+integration: ≥ 85% lines on `app/` (excl. providers/migrations).
- AI eval: golden-set checks mandatory; full-suite eval on promotion.
- E2E: critical journeys only (7) to keep the suite < 10 min.

## CI wiring (see `.github/workflows/ci.yml`)
```
push/PR → backend(lint, mypy, pytest) ∥ frontend(typecheck, build)
main    → (M2+) integration-with-containers job
AI branch → eval job (golden set, calibration) before merge
```
