# API Documentation — NeuroPlant AI

Base URL: `/api/v1` (production: `https://api.neuroplant.ai/api/v1`) ·
Interactive docs: `GET /docs` (Swagger UI) · OpenAPI: `GET /api/v1/openapi.json`

## Conventions

- **Envelope**: `{ "data": … }` on success, `{ "error": { "code", "message", "details? } }` on failure.
- **Errors**: `400` validation · `401` unauthenticated · `403` forbidden (RBAC) ·
  `404` not found · `409` conflict/idempotency · `422` Pydantic · `429` rate-limited · `503` dependency down.
- **Auth**: `Authorization: Bearer <access_token>`. Refresh via `POST /auth/refresh`
  (httpOnly cookie) or refresh-token body. Role gate per route.
- **Idempotency**: `POST /scans`, `/marketplace/orders`, `/payments/*` accept an
  `Idempotency-Key` header (or `client_scan_id`) — safe to retry.
- **Pagination**: list endpoints use `?page=1&page_size=25`; returns `meta.{page,page_size,total}`.
- **Rate limits** (prod): auth `10/min/IP`; scans `20/min/user`; chat `30/min/user`;
  payments `10/min/user`. Headers `X-RateLimit-*` returned.

## Auth & Users

| Method | Path | Access | Description |
|---|---|---|---|
| POST | `/auth/register` | public | create user (phone, password, role) |
| POST | `/auth/login` | public | password login; `202 mfa_required` if MFA on |
| POST | `/auth/otp/send` | public | send phone OTP |
| POST | `/auth/otp/verify` | public | verify OTP → token pair |
| POST | `/auth/mfa/setup` | auth | generate TOTP secret + QR |
| POST | `/auth/mfa/confirm` | auth | verify TOTP code (enables MFA) |
| POST | `/auth/mfa/backup-codes` | auth | regenerate backup codes |
| POST | `/auth/refresh` | public+key | rotate token pair |
| POST | `/auth/logout` | auth | revoke refresh token |
| GET | `/auth/me` | auth | current user |
| GET | `/auth/devices` | auth | registered devices |
| DELETE | `/auth/devices/{id}` | auth | revoke a device |
| GET | `/auth/sessions` | auth | login history |
| GET/PATCH | `/users/me` | auth | read/update profile |

## Catalog

| Method | Path | Description |
|---|---|---|
| GET | `/crops` | list crops (search `?q=`, season filter) |
| GET | `/crops/{id}` | crop detail |
| GET | `/diseases?crop_id=&q=` | list diseases |
| GET | `/diseases/{id}` | disease detail incl. treatments, remedies, prevention |

## Detection & Explainability (M2)

| Method | Path | Description |
|---|---|---|
| POST | `/scans` | multipart: image(s) + `part_type` + `client_scan_id` → diagnosis + heatmap + explanation |
| POST | `/scans/sync` | batch upload of offline queue (idempotent) |
| GET | `/scans?part_type=&disease_id=&from=&to=` | history (search/filter) |
| GET | `/scans/{id}` | scan detail |
| GET | `/scans/{id}/explain` | Grad-CAM heatmap + plain-language explanation |
| DELETE | `/scans/{id}` | soft-delete scan |

## Crop Doctor (M3)

| Method | Path | Description |
|---|---|---|
| POST | `/crop-doctor/series` | create series (crop, plant_name) |
| POST | `/crop-doctor/series/{id}/scans` | attach a scan → health entry |
| GET | `/crop-doctor/series/{id}/timeline` | health score timeline |
| GET | `/crop-doctor/series/{id}/recovery` | recovery graph + expected date |
| GET | `/crop-doctor/series/{id}/report` | latest weekly report (json) |
| GET | `/crop-doctor/series/{id}/report.pdf` | download PDF |

## Soil, Calendar, Yield (M3/M5)

| Method | Path | Description |
|---|---|---|
| POST | `/soil/records` | add soil test record |
| GET | `/soil/history` | soil record history |
| POST | `/soil/{id}/predict-deficiencies` | deficiency predictions + fertilizer plan |
| POST | `/calendar/plans` | create crop plan (sow date, area) |
| GET | `/calendar/plans` | list plans |
| PATCH | `/calendar/events/{id}` | mark done / reschedule |
| GET | `/calendar/upcoming` | next reminders |
| POST | `/yield/estimates` | estimate from this farmer's prior actual harvests; returns null when no baseline exists |
| POST/GET | `/yield/harvests` | record/list actual harvests owned by the farmer |

## Assistant, Voice (M4)

| Method | Path | Description |
|---|---|---|
| POST | `/assistant/chat` | RAG chat (lang-aware, grounded) |
| GET | `/assistant/sessions/{id}/messages` | conversation history |
| POST | `/voice/transcribe` | audio → text + detected lang |
| POST | `/voice/synthesize` | text → audio (lang) |
| POST | `/voice/detect-language` | detect language from text |
| GET | `/voice/commands` | intent/command catalog |

## Weather, Outbreaks, Prices, Schemes (M5)

| Method | Path | Description |
|---|---|---|
| GET | `/weather/current?lat=&lng=` | temp, humidity, rainfall, wind, UV |
| GET | `/weather/forecast?lat=&lng=` | N-day forecast |
| GET | `/weather/risk?crop_id=&lat=&lng=` | per-crop disease risk + factors |
| POST | `/outbreaks/report` | anonymous outbreak report |
| GET | `/outbreaks/map?district=&state=` | aggregated heatmap data |
| GET | `/outbreaks/nearby?lat=&lng=&r=` | nearby reports |
| POST | `/outbreaks/{id}/verify` | expert verify/reject |
| GET | `/market/prices?crop_name=&location=&page=&page_size=` | compare current farmer marketplace offers, with source and last-updated time |
| GET | `/schemes?state_code=&crop_name=&farmer_category=&category=` | filter curated, source-attributed scheme records |
| GET | `/schemes/{id}` | scheme details |
| POST | `/schemes/{id}/eligibility` | compare supplied facts against recorded rules; not a legal determination |
| POST | `/schemes` | add a source-attributed scheme record (admin only) |

Market prices currently come from farmer listings, not an official mandi feed;
historical market observations are not stored. Government schemes are not
seeded with sample data; the API reports an empty catalog until verified
records are curated. Unverified scheme records do not expose subsidy details
or application links.

## Dataset Platform (M4)

| Method | Path | Access | Description |
|---|---|---|---|
| POST | `/dataset/unknown-sample` | auth | submit unknown sample |
| GET | `/dataset/review-queue` | expert/admin | pending samples |
| POST | `/dataset/samples/{id}/label` | expert/admin | label + approve |
| GET | `/dataset/versions` | public | dataset versions |
| GET | `/dataset/models` | public | model registry |

## Marketplace & Store (M6/M7)

| Method | Path | Description |
|---|---|---|
| GET/POST | `/marketplace/listings` | browse / create listing |
| GET/PATCH/DELETE | `/marketplace/listings/{id}` | detail / update inventory / close |
| GET | `/marketplace/listings/{id}/price-recommendation` | AI suggested price |
| POST | `/marketplace/offers` | make offer |
| PATCH | `/marketplace/offers/{id}` | accept / decline / counter |
| GET | `/marketplace/buyers/nearby` | nearby interested buyers |
| POST | `/marketplace/orders` | place order (Razorpay) |
| GET | `/orders` | my orders (buyer/seller views) |
| POST | `/orders/{id}/track` | update tracking / accept or reject |
| GET/POST | `/store/products` | browse / create product |
| GET | `/store/products/{id}` | product detail + reviews |
| POST | `/store/products/{id}/reviews` | review |
| POST | `/store/compare` | compare products |
| GET | `/store/products/{id}/recommend?disease_id=` | AI product recs for a disease |

## Finance & Payments (M6/M10)

| Method | Path | Description |
|---|---|---|
| POST | `/finance/transactions` | manual expense/income |
| GET | `/finance/dashboard` | profit analytics |
| GET | `/finance/export.csv` · `/finance/export.pdf` | reports |
| POST | `/payments/create-order` | create Razorpay order |
| POST | `/payments/verify` | verify client-side signature |
| POST | `/payments/webhook/razorpay` | **public** signed webhook |
| POST | `/payments/payout` | seller/farmer payout |

## Community, Experts, Maps (M5/M8/M9)

| Method | Path | Description |
|---|---|---|
| GET/POST | `/community/posts` | feed / create |
| POST | `/community/posts/{id}/comments` · `/like` · `/share` | interactions |
| GET | `/experts` · `/experts/{id}` · `/experts/{id}/slots` | directory + availability |
| POST | `/appointments` · `/appointments/{id}/cancel` | book/cancel |
| GET | `/maps/nearby?type=&lat=&lng=` | shops/seeds/govt/experts/markets |

## Notifications, Analytics, Admin (M5/M10)

| Method | Path | Description |
|---|---|---|
| GET | `/notifications` | my notifications |
| PATCH | `/notifications/{id}/read` | mark read |
| GET | `/notifications/unread-count` | unread count |
| PATCH | `/notifications/read-all` | mark all visible notifications read |
| GET | `/analytics/agriculture?period_start=&period_end=&crop_id=` | farmer-scoped crop, disease, treatment, calendar, and yield analytics |
| GET | `/analytics/agriculture/export.csv` | export the filtered agricultural report |
| GET | `/analytics/schemes?period_start=&period_end=&crop_name=&state_code=` | farmer-scoped views and eligibility-check aggregates |
| GET/PATCH/POST | `/admin/{users|experts|products|diseases|crops|orders|reports}` | admin CRUD |
| GET | `/admin/audit-log` | admin activity log |

Scheme application status is not tracked. Weather-risk history and measured
soil test results are not persisted, so analytics identify those statistics as
unavailable rather than returning fabricated values.

## WebSocket

| Path | Description |
|---|---|
| `/ws/chat/{conversation_id}` | marketplace / expert chat (JWT handshake) |
| `/ws/notifications/{user_id}` | live notifications |

## Example request/response

```http
POST /api/v1/scans
Authorization: Bearer <token>
Content-Type: multipart/form-data

image=<leaf.jpg> & part_type=leaf & client_scan_id=9f8c…&crop_id=3
```

```json
{
  "data": {
    "id": 1042,
    "disease": { "id": 12, "name": "Tomato Late Blight", "confidence": 0.91 },
    "severity": "moderate",
    "stage": "vegetative",
    "symptoms": ["dark lesions", "white fungal growth on leaf underside"],
    "heatmap_url": "https://cdn.neuroplant.ai/scans/1042/heatmap.png",
    "explanation": "The model focused on the lower leaf surface where irregular, water-soaked lesions form, matching late blight's early pattern. 91% confident.",
    "treatments": { "organic": [...], "chemical": [...], "homemade": [...] },
    "model_version": "disease-v1.2.0"
  }
}
```
