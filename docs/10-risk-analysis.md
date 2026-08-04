# Risk Analysis — NeuroPlant AI

Risk register with likelihood (L), impact (I), and mitigations. `L/I`: H/M/L.

## Risk register

| # | Risk | L | I | Mitigation |
|---|---|---|---|---|
| 1 | **Model accuracy on field images** below expectations (dataset limits) | M | H | Versioned catalog + dataset platform (label→retrain→promote); eval gate blocks promotion; confidence threshold routes low-confidence to cloud fallback; UI surfaces "estimate" labeling; collect-only-verified samples |
| 2 | **Offline detection quality** (reduced class set) misleads farmers | M | H | Clear "offline estimate" badge; re-score on sync; no treatment advice from offline-only results (requires online confirmation or local catalog lookup with disclaimers) |
| 3 | **Payment/payout correctness** (double charge, missed payout) | L | M | Razorpay signature verification; idempotency keys; webhook replay + dead-letter; payout ledger reconciliation task; testnet harness |
| 4 | **Language/voice fidelity** for 12 languages (TTS quality, mis-transcription) | M | M | Hybrid Web Speech + GCP neural voices; auto-detect + persisted pref; TTS always offers text fallback; per-language coverage tests |
| 5 | **Data privacy / DPDP** (crop images, location, financials) | M | H | Images encrypted at rest; consent for anonymous outbreak data; data deletion API; minimal collection; audit logs; DPDP-aligned policy |
| 6 | **Security** (auth bypass, injection, abuse) | M | H | JWT rotation + MFA; argon2; RBAC per route; Pydantic validation; image magic-byte checks; rate limiting; webhook signature checks; OWASP ASVS-aligned review (M11) |
| 7 | **Scalability under load** (scan bursts, live alerts) | M | M | Stateless API + worker pool; async inference off the request path; Redis cache; index strategy; load test in M11 |
| 8 | **Misdiagnosis → harmful treatment advice** | M | H | Treatment content reviewed; safety precautions + "when to call professional" required; AI advice grounded in catalog; expert consultation path; disclaimer UX |
| 9 | **Offline sync conflicts / data loss** | L | M | `client_scan_id` idempotency; server-wins conflict rule; device-encrypted queue; sync digest job; retention policy |
| 10 | **Provider outages** (weather, Razorpay, GCP, LLM) | M | M | Provider adapters + graceful degrade; cached weather; offline queue; health probes; retries via tenacity; LLM rules-fallback |
| 11 | **Schedule slip** (largest risk for a solo build) | H | M | Strict milestone gates; scope-queue for creep; docs/seeders parallelizable; AI curation on GPU/Colab in parallel |
| 12 | **Market/community moderation** (abuse, spam, fake outbreak reports) | M | M | Report limits + rate limits; expert verification for outbreak publish; content moderation (reports); admin tools (M10) |
| 13 | **Financial data accuracy** (auto-logging orders vs manual entries) | M | L | Transactions keyed to related_type/id; reconciliation task; user edit with audit |
| 14 | **Android/iOS later** forcing API rework | L | M | Mobile-ready contracts from day one (versioned REST + WS + JWT + MFA); PWA covers near-term; seams validated in M11 |

## Security threat model (summary)

| Asset | Threat | Control |
|---|---|---|
| User credentials | credential stuffing | argon2, rate limit, OTP, MFA |
| Session | token theft | short-lived access, rotating httpOnly refresh, device revocation |
| Images / personal data | unauthorized access | private buckets + signed URLs, RBAC, encryption at rest |
| Payments | forged webhooks | signature verification + idempotency |
| Admin | privilege abuse | RBAC, audit log, MFA enforced for admin |
| API | DoS / scraping | rate limits, CORS allow-list, validation |

## Dependencies & single points of failure

- **Postgres + Redis** are managed (Railway/Render) → platform SLA + backups.
- **Object storage** R2 — highly available; MinIO for local parity.
- **External providers** (weather/Razorpay/GCP/LLM/video) are optional behind
  adapters with degrade paths — no provider is on the critical path for a scan.

## Monitoring & alerting (M11)

- `/ready` 503s · worker queue depth · webhook failures · model accuracy drift
  (weekly eval vs live) · payout reconciliation mismatches · error rate (Sentry)
  · p95 latency on `/scans`.
