# UI Wireframes — NeuroPlant AI

Design system: **shadcn/ui** tokens · **Tailwind v4** · dark mode default ·
**Framer Motion** transitions · **Recharts** charts · **Leaflet + heatmap** maps ·
mobile-first responsive · persistent **voice bar** + **offline indicator**.

Wireframes below are structural (ASCII). Mobile-first; desktop layouts expand
grids. Interactive states (loading, empty, error, offline) are specced per screen.

## Global shell

```
┌─────────────────────────────────────────────┐
│ ☰ Logo        [Search ▾]       🎤 ◐ 🌙 👤 │   ◐ = online/offline
│ ┌────────────┬─────────────────────────────┐│
│ │ SIDE NAV   │  <route content>            ││
│ │ Dashboard  │                             ││
│ │ Detect     │                             ││
│ │ Crop Doctor│                             ││
│ │ Assistant  │                             ││
│ │ Weather    │                             ││
│ │ Market     │                             ││
│ │ Store      │                             ││
│ │ Community  │                             ││
│ │ Experts    │  ██████ floating voice bar  ││
│ │ Prices     │                             ││
│ │ Finance    │                             ││
│ └────────────┴─────────────────────────────┘│
└─────────────────────────────────────────────┘
```

## 1. Landing
Hero: tagline + live demo "upload a leaf → see it diagnosed" · features grid ·
how-it-works (3 steps) · language switcher · testimonial · app-store/install CTA ·
footer (schemes, contacts).

## 2. Auth (register / login / OTP / MFA)
```
┌──────────────┐
│  Phone +91   │
│  [ +91 98765…]
│  [Continue]  │  → OTP screen (6 boxes)
│  ── or ──    │
│  Email login │
│  Role: (•)Farmer ( )Customer ( )Expert ( )Seller
└──────────────┘
```
MFA: QR + 6-digit entry + backup codes reveal.

## 3. Farmer Dashboard (Smart Farm)
- Crop-health score ring (0–100) per plant · weather card (temp/rain/UV) ·
  disease-risk chip · reminder stack (water/fertilizer/pesticide/harvest) ·
  orders & sales mini-stats · profit estimate · **AI recommendations feed**.

## 4. Disease Detection
```
[ (•) Upload ( ) Camera ]   part: leaf | fruit | stem | plant
┌───────────────┐
│  preview area │  → scanning spinner → result card
└───────────────┘
Result:
  Tomato Late Blight · 91% ██████   severity: moderate · stage: vegetative
  [☰ heatmap]  Original | Grad-CAM   "why? — model focused on lower-leaf lesions…"
  Tabs: Organic | Chemical | Homemade | Fertilizer | Pesticide | Irrigation | Prevent
```

## 5. AI Crop Doctor
Plant series list (multiple) → per plant: health timeline chart, recovery
graph + expected date, per-scan comparison, advice "continue/change/stop
treatment", critical alert banner, weekly PDF download.

## 6. AI Assistant
Chat with mic; language chips; grounded citations to diseases; TTS speaks reply.

## 7. Soil Health
Gauges pH / N / P / K / moisture / OC · deficiency list (deficient/adequate) ·
recommended fertilizer card.

## 8. Crop Calendar
Month/timeline view of events (sowing/water/fert/pesticide/harvest); reschedule;
mark done; seasonal recommendation panel.

## 9. Yield Predictor
Form: crop, area, soil, sow date → predicted yield/income/profit/harvest date +
confidence + factors.

## 10. Weather & Risk + Outbreak map
Current conditions · forecast · disease-risk list · Leaflet map with district
heatmap of verified outbreaks + "report outbreak" button + nearby alerts feed.

## 11. Price Dashboard
Crop selector → live price, history chart, trend badge, nearby markets table,
prediction band.

## 12. Financial Dashboard
Income/expense toggle · donut by category · monthly profit line · add
transaction · export CSV/PDF.

## 13. Marketplace
Browse grid (photos, price, farmer, distance) · listing detail (gallery, qty,
AI suggested price, "Make offer", chat farmer, order) · cart → Razorpay
checkout → tracking timeline · seller view: orders, accept/reject, stock,
delivery.

## 14. Agri Store
Category rails (pesticides/organic/fertilizers/seeds/tools/equipment) · product
card with warranty/expiry badges · compare table (2–4) · reviews · AI "treat
this disease" recommendations block · verified-seller badge.

## 15. Community
Feed (image cards, expert-replied badge) · composer (image + text + disease tag) ·
post detail: comments, likes, shares.

## 16. Experts
Directory (filter: crop/specialization/rating) · profile (creds, reviews) ·
availability slots · booking modal (video/voice/chat) · call screen (Jitsi
embed + chat side panel).

## 17. Dataset Platform (expert/admin)
Review queue list · sample detail (images, symptoms, suggested labels) ·
label picker + approve/reject · dataset/model version table.

## 18. Scan History
Searchable/filterable grid (crop, disease, part, date, offline-pending badge) ·
detail reopens result.

## 19. Analytics / Admin
Farmer: scans over time, disease distribution donut, healthy %, crop analytics,
marketplace analytics. Admin: KPI tiles (users, scans, orders, GMV), manage
tables (users/experts/products/diseases/crops/orders), reports, **audit log**.

## 20. Voice overlay
Floating mic (always accessible) → wave animation → transcript → command
palette chips ("Open marketplace", "Scan leaf", "What to spray?", "Log expense
₹500", "Read notifications") → spoken confirmation · language auto-switch.

---

## Key flows (state notes)

| Flow | States to design |
|---|---|
| Detect | idle → capturing/uploading → scanning (anim) → result | low-confidence → cloud/offline banner → error → retry |
| Offline | online · offline badge · queued count · syncing · conflict resolution toast |
| Order | cart → checkout → paying (Razorpay sheet) → paid → accepted → shipped → delivered · cancelled/refund |
| Appointment | browse → slots → booked → meeting-join (video/voice/chat) → complete/rate |
| Voice | listening → thinking → speaking → command matched/not-matched fallback help |
