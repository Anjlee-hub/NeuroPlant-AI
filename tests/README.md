# NeuroPlant AI — Cross-cutting tests

Beyond per-service suites (`backend/tests`, `frontend` Vitest), this directory
holds **integration** and **end-to-end** tests that span the stack:

- `integration/` — API ↔ Postgres ↔ Redis ↔ worker (Docker Compose, M2+)
- `e2e/` — Playwright flows against the real app (M2+)

Strategy and matrix: `docs/11-testing-strategy.md`.
