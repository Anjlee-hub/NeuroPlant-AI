# Product Requirements Document — NeuroPlant AI

**Version:** 1.0 · **Date:** 2026-08-04 · **Status:** Approved (architecture v2)

---

## 1. Vision

Empower every farmer in India with an AI crop doctor in their pocket — detect
diseases in seconds, get treatments they trust (organic and chemical),
monitor recovery over time, and run their entire farm business (weather,
calendar, yield, marketplace, agri-store, experts, community) — **in their own
language, with their own voice, even on a weak connection**.

## 2. Personas

| Persona | Goals | Pain points addressed |
|---|---|---|
| **Ramesh — Smallholder Farmer** (primary) | Detect disease, cheap/trusted treatment, sell surplus at fair price | No nearby agronomist; crop destroyed before advice arrives; no market access |
| **Priya — Commercial Farmer** | Monitor many plants, plan calendar/yield, financials | Manual record-keeping; guesswork on fertilizer/water |
| **Anita — Customer** | Buy fresh produce directly from nearby farmers | Middlemen margins; no provenance |
| **Dr. Venkatesh — Agricultural Expert** | Consult remotely, verify disease reports, grow reputation | Travel cost; one visit reaches few farmers |
| **Meena — Agri Shop Seller** | Reach farmers with verified products | Limited local customer base; no AI product match |
| **Admin / NeuroPlant Ops** | Curate catalog, verify sellers/experts, ensure data quality | Manual moderation; no analytics |

## 3. Feature Requirements (with acceptance criteria)

> Priority: **P0** = launch-blocking · **P1** = high value · **P2** = enhance.

### 3.1 AI Disease Detection — **P0** (M2)
- Upload **leaf / fruit / stem / whole-plant** image (file or camera capture).
- System returns: predicted disease, **confidence (explained)**, severity, stage, symptoms.
- **Grad-CAM heatmap** overlay highlights affected regions; plain-language why.
- AC: end-to-end detect in ≤ 5 s p95 (online); confidence ≥ 0.6 flags low-confidence path.
- **Offline**: reduced-class on-device inference + queued sync. AC: a scan made offline appears in history with an "offline estimate" badge and syncs automatically on connectivity.

### 3.2 Treatment Recommendation Engine — **P0** (M3)
- Per disease: **organic, chemical, homemade/kitchen, traditional, biological** treatments; recommended **fertilizers, pesticides, nutrients, irrigation**; recovery time; prevention tips; safety precautions and "when to call a professional".
- AC: every catalogued disease has ≥ 1 treatment in each category or an explicit gap notice.

### 3.3 AI Crop Doctor — **P0** (M3)
- Track **multiple plants separately**; add scans over days/weeks.
- Outputs: **health score (0–100)**, trend, **treatment effectiveness** per scan, **recovery graph + expected recovery date**, critical alerts, **weekly PDF report**, confidence explanation per scan.
- AC: a 3-scan improving series shows rising score; a worsening series triggers an alert.

### 3.4 Personal AI Farming Assistant — **P0** (M3/M4)
- Learns: crops, farm size, soil, previous diseases, treatments, watering, weather, location, scan history.
- Personalized recommendations (not generic). Chat in user's language + voice.
- AC: recommendations differ by farmer profile; grounded in catalog (no hallucinated advice).

### 3.5 Voice-First + Multilingual — **P0** (M4)
- **12 languages**: en, hi, kn, ta, te, ml, mr, gu, pa, bn, or, ur.
- Voice: navigation, search, forms, notifications, chatbot. Auto language detection; persisted preference.
- AC: a Hindi-speaking user can complete "scan leaf → read result → set reminder" by voice alone.

### 3.6 Soil Health — **P1** (M3)
- Record pH, N, P, K, moisture, organic carbon; predict deficiencies; recommend fertilizer.
- AC: a soil record yields deficiency predictions + fertilizer plan for the crop.

### 3.7 Smart Crop Calendar — **P1** (M3)
- Sowing, watering, fertilizer, pesticide, harvest events with reminders and seasonal recs.
- AC: creating a crop plan generates a dated event schedule with notification reminders.

### 3.8 Crop Yield Prediction — **P1** (M5)
- Predicted yield, income, profit/loss, harvest date from crop + soil + weather + history.
- AC: shows confidence and feature basis; rule-baseline floor until data accrues.

### 3.9 Weather Intelligence — **P0** (M5)
- Temp, humidity, rainfall, wind, UV; **disease-risk prediction**; crop recommendation.
- AC: risk endpoint returns per-crop disease risk with driving factors.

### 3.10 Crowd-Sourced Outbreak Intelligence — **P1** (M5)
- Anonymous outbreak reports; district/state **heatmaps**; notify nearby farmers; expert verification.
- AC: a verified report updates the heatmap and notifies farmers within the radius.

### 3.11 Marketplace (Farmer → Customer) — **P0** (M6)
- Listings, inventory, orders, **Razorpay checkout + payouts**, tracking, ratings, chat.
- **Negotiation (offers/counter)**, **AI price recommendation**, **nearby buyers**, delivery-partner adapter.
- AC: full order lifecycle incl. payment + payout; offers can be accepted/declined/countered.

### 3.12 Agri Store (Seller → Farmer) — **P0** (M7)
- Verified sellers; pesticides/organics/fertilizers/seeds/tools/equipment; search/compare/reviews; **AI "treat this disease" product recs**; warranty/expiry management.
- AC: sellers cannot list without verification; expired products are flagged.

### 3.13 Community — **P1** (M8)
- Posts, images, comments, likes, shares; expert replies; disease discussions.

### 3.14 Expert Consultation — **P1** (M9)
- Directory, slots, appointment booking, **video/voice/chat** calls (Jitsi default).

### 3.15 Price Dashboard — **P1** (M5)
- Live/historical prices, trends, nearby markets, prediction.

### 3.16 Financial Dashboard — **P1** (M6/M10)
- Expense/income tracking, profit analytics, CSV/PDF export; auto-logged from orders/store.

### 3.17 Government Schemes — **P2** (M10)
- Subsidies, loans, insurance, welfare — searchable by state/category.

### 3.18 Notifications — **P0 cross-cutting**
- Weather, disease outbreak, water, pesticide, harvest, order updates (in-app + push, TTS-read).

### 3.19 Maps — **P1** (M5)
- Nearby agri shops, seed stores, govt offices, experts, markets.

### 3.20 Analytics + Admin — **P1** (M10)
- Farmer dashboard; admin manage users/experts/products/diseases/crops/orders/reports + audit log.

### 3.21 Dataset Collection Platform — **P1** (M4)
- Unknown diseases stored separately; experts label; approved images expand the dataset; **dataset + model versioning** with retrain-on-approve.

## 4. Non-Functional Requirements

| Category | Requirement |
|---|---|
| Performance | API p95 < 300 ms (excl. AI inference); scan pipeline p95 < 5 s |
| Availability | ≥ 99.5% for read services; graceful degradation for offline/AI/voice |
| Scalability | Horizontal: stateless API + worker pool; modular monolith → extractable services |
| Security | OWASP ASVS-aware; JWT rotation + MFA; RBAC; rate limits; image validation; audit logs |
| Privacy | Scan images encrypted at rest; consent for anonymous outbreak data; GDPR/DPDP-aligned |
| Accessibility | Mobile-first; voice-first; contrast-safe; keyboard navigable |
| i18n | 12 languages; RTL-safe where needed (Urdu); persisted preference |
| Offline | PWA installable; core detection + history usable with no connectivity |

## 5. Success Metrics

- Activation: ≥ 60% of registered users complete a scan within 7 days.
- Accuracy: disease top-1 accuracy ≥ 90% on eval set for launched crops; confidence calibrated (ECE < 0.1).
- Retention: D30 ≥ 35% (offline + reminders drive habit).
- Commerce: ≥ 5% of monthly active users place an order.
- Trust: expert verification SLA < 48h; outbreak false-positive rate < 5%.

## 6. Out of Scope (v1)

- Real IoT/drone/satellite ingestion (designed-for, not delivered).
- KYC provider integration (manual seller/expert verification).
- Livestock management; smart-irrigation actuators.
