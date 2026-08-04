# NeuroPlant AI — Backend

FastAPI + SQLAlchemy 2.0 (async) + Celery + PostgreSQL service.

## Layout

```
app/
├── main.py            # ASGI entrypoint, CORS, router registration
├── core/              # config, logging, (M1: security, rate limiting)
├── api/
│   ├── health.py      # /health (liveness), /ready (readiness)
│   └── v1/            # versioned domain routers (added per milestone)
├── db/                # async engine/session factories, declarative Base
├── services/          # business logic (per milestone)
├── ai/                # classifier adapters, Grad-CAM, crop doctor (M2/M3)
├── integrations/      # razorpay, gcp-speech, weather, s3, … (M2+)
├── workers/           # Celery tasks (M2+)
└── ws/                # WebSocket managers (M2+)
tests/                 # pytest suite
```

## Local dev (no Docker, no Postgres required)

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate    |    POSIX: source .venv/bin/activate
pip install -e ".[dev]"
uvicorn app.main:app --reload        # → http://localhost:8000/docs
pytest                              # run the test suite
```

Native dev uses **SQLite** (`DATABASE_URL=sqlite+aiosqlite:///./neuroplant.db`) and
**Celery eager mode** so the stack runs with zero external services. Production
uses PostgreSQL + Redis — see `docker/docker-compose.yml` and `docs/06-deployment.md`.

## Configuration

All settings via environment / `.env` (see `app/core/config.py`). Copy
`docker/.env.example` → `.env` for the full production-style surface.
