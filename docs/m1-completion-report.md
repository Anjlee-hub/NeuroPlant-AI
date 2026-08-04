# M1 Completion Report — Authentication, Landing, Database & PWA Shell

**Milestone:** M1 · **Status:** Implemented — awaiting approval
**Tag:** `v0.1.0-m1` · **Branch:** `main`
**Date:** 2026-08-04

---

## 1. Overview

M1 delivers the foundation the rest of the platform builds on: a complete
identity & auth backend (roles, password/OTP login, JWT rotation, MFA, device
management, login history), the catalog seeders, the full React application
shell (router, providers, i18n en/hi, dark mode, PWA + offline layer), and the
landing + auth pages. All changes are committed on `main` and the working tree
is clean.

## 2. Features Completed

### Backend — Identity & Auth (`backend/app/`)
- **Registration** with role selection (`farmer | customer | expert | seller`),
  phone/email uniqueness checks, optional password (phone-only OTP signup).
- **Password login** (phone or email identifier) with argon2 password hashing.
- **Phone OTP login** — codes stored hashed with expiry + attempts cap;
  the code is echoed in the API response *only* when `settings.debug` is true
  (dev testability, never in production).
- **JWT access/refresh rotation** — separate access/refresh secrets, `type`
  claim enforcement, `exp`/`nbf`/`iat`; refresh tokens stored as SHA-256 hashes
  with **reuse detection** that revokes the whole session family on replay.
- **MFA (TOTP)** — provisioning (QR + secret + otpauth URI), enable-with-verify,
  single-use hashed backup codes (10), regeneration, and a signed 10-minute
  challenge for password+MFA login.
- **Device management** — fingerprint via `X-Device-Id` headers, list/revoke.
- **Login history** (`/auth/sessions`) — method, success, MFA usage, IP/UA.
- **RBAC** via `require_roles` dependency (403 on insufficient role).
- **Alembic migration** `e7a4341cf99e` (initial schema: identity, auth, catalog)
  — verified `upgrade head` clean on a fresh database.
- **Seeders** for the crop + disease catalog (`app/db/seed.py`, `seed_data.py`).

### Frontend — Shell, Landing, Auth UI (`frontend/src/`)
- **App shell** — `RootLayout` (header/footer), `ErrorBoundary`, router
  (`/`, `/login`, `/login/mfa`, `/register`, `/settings/mfa`, feature stubs,
  `404`), React Query + Theme providers.
- **i18n** — i18next with `en`/`hi` packs, browser language detection,
  `<html lang>` sync, language switcher in the header.
- **Dark mode** — class-based `ThemeProvider` (light/dark/system) + toggle.
- **Landing page** — hero, 6 feature highlights, how-it-works, testimonials,
  CTA, scroll-reveal motion.
- **Auth pages** — register (role cards), login (password + phone OTP tabs),
  MFA challenge verify, MFA enrollment (QR → confirm → backup codes).
- **PWA** — `vite-plugin-pwa` (generateSW, auto-update, installable, manifest
  icons) + **offline layer** (`offline/`): IndexedDB `syncQueue` + `kv` stores,
  connectivity store, ordered sync queue with per-type handlers and a
  5-attempt drop, `startSyncLoop` on boot/`online`.
- **Typed API client** (`lib/api.ts`) + **zustand auth store** (`stores/auth.ts`)
  with boot-time session hydration.

## 3. Files Created / Modified

### Backend
```
app/core/config.py            app/core/logging.py        app/core/security.py
app/main.py                   app/api/health.py
app/api/v1/router.py          app/api/v1/deps.py
app/api/v1/endpoints/auth.py  app/api/v1/endpoints/users.py
app/db/session.py             app/db/seed.py             app/db/seed_data.py
app/models/base.py            app/models/user.py         app/models/catalog.py
app/schemas/auth.py           app/schemas/user.py
app/services/auth.py          app/services/otp.py
app/workers/celery_app.py     app/workers/tasks.py
alembic/versions/e7a4341cf99e_initial_schema_identity_auth_catalog.py
tests/conftest.py             tests/test_auth.py         tests/test_health.py
tests/test_seed.py            pyproject.toml             README.md
```

### Frontend
```
src/App.tsx                   src/main.tsx               src/i18n.ts
src/app/{providers,router,error-boundary,theme-provider}.tsx
src/components/auth-shell.tsx src/components/language-switcher.tsx
src/components/theme-toggle.tsx  src/components/offline-indicator.tsx
src/components/layout/{root-layout,header,footer,auth-nav}.tsx
src/components/ui/{button,card,input,label,badge}.tsx
src/hooks/use-language.ts     src/lib/{api,utils}.ts     src/stores/auth.ts
src/offline/{db,network,sync}.ts
src/pages/{home,login,register,mfa-verify,mfa-setup,coming-soon,not-found}.tsx
src/types/auth.ts             src/styles/globals.css
src/locales/{en,hi}.json      src/vite-env.d.ts
src/test/setup.ts             src/{components,pages}/__tests__/*.test.tsx
vitest.config.ts              eslint.config.js           vite.config.ts
package.json                  tsconfig.{app,node}.json   index.html
```

### Repo root / infra
```
docker/docker-compose.yml     docker/Dockerfile.api      docker/Dockerfile.web
docker/nginx/nginx.conf       docker/.env.example        README.md
```

## 4. API Endpoints Implemented (`/api/v1`)

| Method | Path | Auth | Purpose |
|---|---|---|---|
| POST | `/auth/register` | — | Register + auto-login (201) |
| POST | `/auth/login` | — | Password login (may return MFA challenge) |
| POST | `/auth/otp/send` | — | Send phone OTP (debug code only in dev) |
| POST | `/auth/otp/verify` | — | Verify OTP → token pair |
| POST | `/auth/refresh` | — | Rotate refresh token (reuse detection) |
| POST | `/auth/logout` | — | Revoke refresh token (204) |
| GET | `/auth/me` | bearer | Current user profile |
| POST | `/auth/mfa/setup` | bearer | Provision TOTP secret |
| POST | `/auth/mfa/confirm` | bearer | Enable MFA → backup codes |
| POST | `/auth/mfa/backup-codes` | bearer | Regenerate backup codes |
| POST | `/auth/mfa/verify` | — | Complete MFA challenge |
| GET | `/auth/devices` | bearer | List trusted devices |
| DELETE | `/auth/devices/{device_id}` | bearer | Revoke a device (204) |
| GET | `/auth/sessions` | bearer | Login history |
| GET | `/users/me` | bearer | User profile (alias) |

Ops: `GET /health` (liveness) · `GET /ready` (readiness) · `GET /docs` ·
`GET /api/v1/openapi.json`. OpenAPI lists **17 paths** under `/api/v1`.

## 5. Database Tables Created (12)

`users` · `mfa` · `refresh_tokens` · `devices` · `login_events` · `otp_codes` ·
`farmer_profiles` · `expert_profiles` · `seller_profiles` · `crops` ·
`diseases` · `alembic_version`

Migration: `e7a4341cf99e` — verified clean on a fresh SQLite DB
(`alembic upgrade head`).

## 6. Test Results

| Suite | Result |
|---|---|
| Backend `pytest` | **27 passed** (auth, health, seed) |
| Backend `ruff check .` | clean |
| Backend `ruff format --check .` | 37 files formatted |
| Backend `mypy app` | clean (31 source files) |
| Frontend `vitest run` | **10 passed** (language-switcher, theme-toggle, login) |
| Frontend `tsc -b` typecheck | clean |
| Frontend `vite build` (PWA) | clean (11 precache entries) |
| Frontend `eslint .` (`--max-warnings=0`) | clean |

## 7. Verification Performed

- **Migrations on a fresh DB** — `alembic upgrade head` → 12 tables, clean.
- **API docs** — `/api/v1/openapi.json` (17 paths) and `/docs` serve.
- **Native app start** — backend (uvicorn) and frontend (vite) both boot;
  `/health`, `/ready`, protected-route 401 confirmed.
- **Live end-to-end auth smoke** — `register → login → /me` (valid token) and
  401 for a garbage token, against the running server.
- **Docker (static validation)** — `docker-compose.yml`, `Dockerfile.api`,
  `Dockerfile.web`, nginx config and `.env.example` are coherent. Full compose
  boot is deferred to a Docker-capable host (M11).

## 8. Known Limitations & Recommendations

1. **Tokens stored in `localStorage`** — the architecture plan calls for an
   *httpOnly* refresh cookie. XSS can read localStorage. Mitigations in place:
   short-lived access tokens, refresh rotation, MFA. **Recommend:** move the
   refresh token to an httpOnly+Secure cookie (with CSRF handling) during M11
   hardening.
2. **No automatic frontend token refresh** — access tokens expire (30 min) and
   the next authenticated call 401s, logging the user out. `/auth/refresh`
   works and is tested. **Recommend:** a single-flight refresh interceptor in
   `lib/api.ts` (must serialize concurrent 401s to avoid double-rotation
   tripping reuse revocation) — M2.
3. **Dev JWT secrets are defaulted** in `app/core/config.py` —
   `jwt_secret` / `jwt_refresh_secret` **must** be overridden via environment in
   production.
4. **Rate limiting is disabled by default** (`rate_limit_enabled=False`).
   Enable it in production — auth/OTP endpoints are the first candidates.
5. **SMS/WhatsApp provider is a stub** — `# TODO(M2)` in `services/otp.py`;
   native dev echoes the code in `debug` mode only.
6. **Offline sync has no handlers yet** — the queue/loop is in place; M2
   registers the `scan` type. Unknown types are dropped by design.
7. **Stale dev server on :8000** — a pre-M1 uvicorn may still be listening on
   port 8000; kill it before `npm run dev` so the vite proxy targets the
   current build.

## 9. Commit History (M1 + finalization)

```
ca52378 build(docker): use npm ci for reproducible frontend image builds
f13f50e chore(frontend): add ESLint flat config (ESLint 10, typescript-eslint)
21912fe test(frontend): add Vitest harness + component tests for M1 shell
b97d1cb tooling: exclude autogenerated Alembic migrations from ruff
bde358d M1: MFA enrollment page + header security link
caef5f3 M1: login (password/OTP) + MFA challenge pages
d26c656 M1: landing page — hero, features, how-it-works, testimonials, CTA
0c639b1 M1: auth foundation — API client, auth store, session header
9e41023 M1: PWA offline layer — SW + IndexedDB store + sync queue
bcaecf0 M1: app shell — router, providers, layout, i18n wiring
```
