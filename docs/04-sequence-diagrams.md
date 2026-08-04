# Sequence Diagrams — NeuroPlant AI

Key flows rendered as Mermaid sequence diagrams. Rendered on GitHub, GitLab, or
[mermaid.live](https://mermaid.live).

## 1. Authentication (password + MFA)

```mermaid
sequenceDiagram
    autonumber
    actor F as Farmer
    participant W as Web App (PWA)
    participant A as Auth API
    participant D as Postgres
    participant T as TOTP (Authenticator)

    F->>W: enter phone + password
    W->>A: POST /auth/login
    A->>D: verify argon2 hash
    alt MFA enabled
        A-->>W: 202 mfa_required (challenge)
        F->>T: read 6-digit code
        F->>W: enter code
        W->>A: POST /auth/mfa/confirm
    end
    A->>D: record login_event + device
    A-->>W: access_token + refresh_token (httpOnly)
    W->>A: GET /auth/me
```

## 2. Disease scan (upload → AI → explain → persist)

```mermaid
sequenceDiagram
    autonumber
    actor F as Farmer
    participant W as Web App
    participant API as Scans API
    participant S3 as Object Storage
    participant AI as DiseaseClassifier (local TF → cloud fallback)
    participant DB as Postgres
    participant OB as Outbox → Notifications

    F->>W: select/capture leaf image
    W->>API: POST /scans (client_scan_id, part_type, image)
    API->>API: validate image (magic bytes, size, type)
    API->>S3: store original → MediaItem
    API->>AI: predict(MediaItem)
    alt top-1 confidence < 0.6
        AI->>AI: cloud fallback classifier
    end
    AI-->>API: disease, confidence, severity, stage, symptoms
    API->>AI: explain(scan) → Grad-CAM heatmap
    AI-->>API: heatmap_url + plain-language explanation
    API->>DB: insert scan (idempotent by client_scan_id)
    API->>OB: publish scan.completed
    OB-->>W: push notification "Scan complete"
    API-->>W: 201 scan result (disease, confidence, heatmap, explanation)
```

## 3. Offline scan → auto-sync

```mermaid
sequenceDiagram
    autonumber
    actor F as Farmer
    participant W as Web App
    participant IDB as IndexedDB
    participant TFJS as TF.js (on-device)
    participant Sync as Sync Engine
    participant API as Scans API

    Note over F,W: offline
    F->>W: capture leaf image
    W->>TFJS: offline inference (reduced class set)
    TFJS-->>W: estimate {disease, confidence}
    W->>IDB: persist scan (status=offline_estimate, client_scan_id)
    W-->>F: result labelled "offline estimate"

    Note over F,W: connectivity restored
    Sync->>IDB: drain queue
    Sync->>API: POST /scans/sync (batch, client_scan_id)
    API-->>Sync: server results (idempotent merge)
    Sync->>IDB: mark synced; store authoritative server result
    W-->>F: badge cleared; full-catalog result shown
```

## 4. Marketplace order + payment (Razorpay)

```mermaid
sequenceDiagram
    autonumber
    actor C as Customer
    actor Fm as Farmer (Seller)
    participant W as Web App
    participant API as Marketplace API
    participant RZ as Razorpay
    participant DB as Postgres
    participant OB as Outbox

    C->>W: place order (listings, qty)
    W->>API: POST /marketplace/orders
    API->>DB: create order (status=pending)
    API->>RZ: create Razorpay Order (idempotency key)
    RZ-->>API: razorpay_order_id
    API-->>W: checkout payload
    C->>RZ: pay (UPI/card)
    RZ->>API: webhook payment.captured (signed)
    API->>API: verify signature
    API->>DB: order status=paid; stock decrement
    API->>OB: publish order.paid
    OB-->>W: notify farmer "new paid order"
    API->>RZ: payout to farmer (on delivery)
    OB-->>C: notify "order accepted"
```

## 5. Crowd-sourced outbreak: report → verify → notify

```mermaid
sequenceDiagram
    autonumber
    actor F as Farmer (anonymous)
    actor E as Expert
    participant API as Outbreaks API
    participant DB as Postgres
    participant OB as Outbox
    participant W as Nearby Farmers

    F->>API: POST /outbreaks/report (lat/lng, crop, symptoms, images)
    API->>DB: insert (status=pending, anon_ref)
    API-->>F: 201 "report received"

    E->>API: GET /outbreaks/review-queue
    E->>API: POST /outbreaks/{id}/verify (verified/rejected)
    API->>DB: status=verified; verification recorded
    alt verified
        API->>OB: publish outbreak.verified
        OB->>W: notify farmers within radius "outbreak in your area"
        API->>DB: aggregate district/state heatmap data
    end
```

## 6. Dataset platform: label → retrain → promote

```mermaid
sequenceDiagram
    autonumber
    actor F as Farmer
    actor E as Expert
    participant API as Dataset API
    participant DB as Postgres
    participant W as Celery Worker
    participant OB as Outbox

    F->>API: POST /dataset/unknown-sample (images, symptoms)
    API->>DB: insert (status=pending)

    E->>API: GET /dataset/review-queue
    E->>API: POST /dataset/samples/{id}/label (disease_id)
    API->>DB: status=approved, dataset_version=v2
    API->>OB: publish dataset.approved
    OB->>W: ingest images into dataset v2
    W->>W: retrain model → metrics.json
    W->>DB: register model_versions (status=staging)
    W->>DB: run eval gate (accuracy ≥ threshold)
    W->>DB: promote to production (zero code change)
    API->>W: scans now served by model v2
```

## 7. Voice command flow

```mermaid
sequenceDiagram
    autonumber
    actor F as Farmer
    participant V as Voice Layer
    participant STT as SpeechService (Web Speech / GCP)
    participant INT as Intent Router
    participant FE as Feature
    participant TTS as SpeechService (TTS)

    F->>V: tap mic, speak "खोलो मार्केटप्लेस"
    V->>STT: transcribe (auto-detect language hi)
    STT-->>V: text + lang
    V->>INT: classify intent → {action: navigate, target: marketplace}
    INT->>FE: route + payload (marketplace)
    FE-->>V: ack phrase (localized)
    V->>TTS: synthesize ack in hi
    TTS-->>F: spoken confirmation
```

## 8. AI Crop Doctor — health tracking over time

```mermaid
sequenceDiagram
    autonumber
    actor F as Farmer
    participant API as CropDoctor API
    participant DB as Postgres
    participant W as Celery Worker

    F->>API: POST /crop-doctor/series (crop, plant_name)
    loop each scan added
        F->>API: POST /crop-doctor/series/{id}/scans
        API->>API: compute health_score, trend
        API->>DB: insert crop_health_entry
    end
    F->>API: GET /crop-doctor/series/{id}/report
    API->>W: generate weekly PDF (async)
    W->>DB: store health_reports.pdf_url
    W-->>API: pdf_url
    API-->>F: download PDF + recovery graph + advice
```
