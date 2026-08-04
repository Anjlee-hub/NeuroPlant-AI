# NeuroPlant AI 🌱

**AI-powered Agriculture Platform** — connecting Farmers, Customers, Experts, and Agricultural Sellers/Shops.

An all-in-one, offline-first, voice-first, 12-language platform for Indian agriculture: AI disease detection with explainability, treatment recommendations, a continuous AI Crop Doctor, a personal AI farming assistant, soil health, a smart crop calendar, crop-yield prediction, weather & disease-risk intelligence, crowd-sourced outbreak heatmaps, price dashboards, a financially-instrumented marketplace, agri-store, community, expert consultation, analytics, and admin tooling.

> **Status:** Milestone 0 (scaffold + documentation pack) complete. **Milestone 1
> (auth, landing, database, PWA shell) implemented and awaiting approval** — see
> [`docs/m1-completion-report.md`](docs/m1-completion-report.md). Each milestone
> ships and stops for approval — see `docs/09-milestone-timeline.md`.

---

## Monorepo Layout

```
neuroplant-ai/
├── frontend/     React + Vite + TypeScript + Tailwind + shadcn/ui (PWA, offline-first)
├── backend/      FastAPI + SQLAlchemy 2.0 (async) + Celery + PostgreSQL
├── ai/           Training pipelines (disease / yield), versioned model registry
├── database/     Postgres bootstrap SQL + seeders (crops, diseases, treatments, schemes)
├── docker/       docker-compose local stack + Dockerfiles + nginx
├── docs/         The Documentation Pack (PRD, SAD, ER, APIs, deployment, roadmap, …)
├── tests/        Cross-cutting integration / e2e tests
└── .github/      CI + deploy workflows
```

## Quick Start (native — no Docker required)

```bash
# Backend (Python 3.13)
cd backend
python -m venv .venv && source .venv/bin/activate   # or .venv\Scripts\activate on Windows
pip install -e ".[dev]"
alembic upgrade head                                  # create/apply the schema (SQLite by default)
uvicorn app.main:app --reload                        # → http://localhost:8000/docs

# Frontend (Node 20+)
cd frontend
npm install --include=dev                             # see NODE_ENV note below
npm run dev                                          # → http://localhost:5173
```

> **Windows note:** the shell exports `NODE_ENV=production` globally, which makes
> plain `npm install` skip devDependencies. Use `npm install --include=dev`
> (or `NODE_ENV= npm install`) for a full dev setup.

Local dev uses a **SQLite fallback** + **Celery eager mode** so the full stack runs with zero external services. Production and the containerized stack use **PostgreSQL + Redis + MinIO/S3** — see `docker/docker-compose.yml` and `docs/06-deployment.md`.

## Quality gates

```bash
# Backend
cd backend && .venv/Scripts/python.exe -m pytest     # 27 tests
.venv/Scripts/python.exe -m ruff check .
.venv/Scripts/python.exe -m ruff format --check .
.venv/Scripts/python.exe -m mypy app

# Frontend
cd frontend && npm test                              # Vitest + Testing Library
npm run lint                                         # ESLint (flat config)
npm run typecheck                                    # tsc -b --noEmit
npm run build                                        # tsc -b && vite build (PWA)
```

## Documentation Pack

| # | Doc | Purpose |
|---|---|---|
| 1 | [`docs/01-prd.md`](docs/01-prd.md) | Product Requirements Document |
| 2 | [`docs/02-sad.md`](docs/02-sad.md) | Software Architecture Document |
| 3 | [`docs/03-er-diagram.md`](docs/03-er-diagram.md) | Database ER diagram |
| 4 | [`docs/04-sequence-diagrams.md`](docs/04-sequence-diagrams.md) | Key flows as sequence diagrams |
| 5 | [`docs/05-api.md`](docs/05-api.md) | REST API reference |
| 6 | [`docs/06-deployment.md`](docs/06-deployment.md) | Deployment topology (Railway/Render) |
| 7 | [`docs/07-ui-wireframes.md`](docs/07-ui-wireframes.md) | UI wireframes |
| 8 | [`docs/08-ai-pipeline.md`](docs/08-ai-pipeline.md) | AI training → serving → dataset loop |
| 9 | [`docs/09-milestone-timeline.md`](docs/09-milestone-timeline.md) | Milestones, scope, estimates |
| 10 | [`docs/10-risk-analysis.md`](docs/10-risk-analysis.md) | Risks & mitigations |
| 11 | [`docs/11-testing-strategy.md`](docs/11-testing-strategy.md) | Test strategy & matrix |
| 12 | [`docs/12-roadmap.md`](docs/12-roadmap.md) | Post-launch roadmap (drone, IoT, mobile) |

## License

Proprietary. © NeuroPlant AI.
