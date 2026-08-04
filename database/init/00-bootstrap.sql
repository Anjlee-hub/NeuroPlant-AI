-- NeuroPlant AI — PostgreSQL bootstrap.
-- Applied to the Postgres database before Alembic migrations.
-- Native-dev SQLite does not use this file (SQLite has no extensions).

-- citext: case-insensitive text (phone/email lookups).
CREATE EXTENSION IF NOT EXISTS citext;

-- pgcrypto: gen_random_uuid() used for client-generated idempotency keys.
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- Note: PostGIS is intentionally NOT enabled in v1 (heavy dependency).
-- Geo lookups use simple lat/lng columns + a bounding-box filter; if drone /
-- satellite geospatial queries arrive (roadmap), PostGIS can be added later.
