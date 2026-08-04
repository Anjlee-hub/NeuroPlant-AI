# NeuroPlant AI — Database

PostgreSQL bootstrap + seeders. Schema migrations are managed with **Alembic**
in `backend/alembic/` (the source of truth); the `init/` SQL here only covers
Postgres-specific bootstrap (extensions) and `seed/` holds idempotent seeders.

```
database/
├── init/     # 00-bootstrap.sql — extensions (citext, pgcrypto), tuning
└── seed/     # python + SQL seeders: crops, diseases, treatments,
              # schemes, markets, soil calibration, calendar templates
```

Run seeders: `python -m database.seed` (from repo root, `DATABASE_URL` env set)
or via Celery task in CI. Seeding is idempotent (upsert by natural key).
