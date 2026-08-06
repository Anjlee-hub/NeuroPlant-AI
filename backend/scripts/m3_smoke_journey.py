"""M3 Task 7 — end-to-end API smoke journey.

Walks the complete user journey against a live backend:
register → login → upload scan → detection → explain → recommendations →
soil → recovery (+log) → calendar (crops → schedule → dashboard) →
voice assistant (en + hi) → history → profile → sessions/devices → offline sync.

Run with the live backend reachable at BASE (start: uvicorn app.main:app --port 8001).
    ./.venv/Scripts/python.exe scripts/m3_smoke_journey.py
"""

import base64
import io
import uuid
from datetime import date

import httpx
from PIL import Image

BASE = "http://127.0.0.1:8001"
API = f"{BASE}/api/v1"

passed = []
failed = []


def check(name: str, cond: bool, detail: str = ""):
    if cond:
        passed.append(name)
        print(f"  ok  {name}")
    else:
        failed.append(name)
        print(f"  FAIL {name} — {detail}")


def jpeg_bytes() -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (224, 224), (120, 90, 60)).save(buf, format="JPEG")
    return buf.getvalue()


def main() -> None:
    client = httpx.Client(base_url=API, timeout=30)

    # ── Pre-flight ─────────────────────────────────────────────────────────
    r = client.get(f"{BASE}/ready")
    check("GET /ready", r.status_code == 200, r.text)
    r = client.get(f"{BASE}/health")
    check("GET /health", r.status_code == 200, r.text)

    # ── Register + login ───────────────────────────────────────────────────
    phone = f"9{str(uuid.uuid4().int)[:9]}"  # 9 + 9 digits = 10 digits
    payload = {"phone": phone, "name": "Smoke Tester", "role": "farmer", "password": "secret123"}
    r = client.post("/auth/register", json=payload)
    check("POST /auth/register (201)", r.status_code == 201, f"{r.status_code}: {r.text[:200]}")
    tokens = r.json()
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    r = client.post("/auth/login", json={"identifier": phone, "password": "secret123"})
    check("POST /auth/login (200)", r.status_code == 200, r.text[:200])
    headers = {"Authorization": f"Bearer {r.json()['access_token']}"}

    r = client.get("/auth/me", headers=headers)
    check("GET /auth/me", r.status_code == 200 and r.json()["phone"] == phone, r.text[:200])

    # ── Catalog (filter options) ───────────────────────────────────────────
    r = client.get("/catalog/crops", headers=headers)
    crops = r.json()["items"] if r.status_code == 200 and "items" in r.json() else r.json()
    check("GET /catalog/crops", r.status_code == 200 and len(crops) > 0, r.text[:200])
    tomato = next((c for c in crops if c.get("name") == "tomato"), crops[0])
    crop_id = tomato["id"]

    # ── Upload + AI detection ──────────────────────────────────────────────
    scan_id = str(uuid.uuid4())
    r = client.post(
        "/scans",
        files=[("files", ("leaf.jpg", jpeg_bytes(), "image/jpeg"))],
        data={"client_scan_id": scan_id, "crop_id": crop_id, "part_type": "leaf"},
        headers=headers,
    )
    check("POST /scans (201) — detection", r.status_code == 201, f"{r.status_code}: {r.text[:300]}")
    scan = r.json()
    scan_pk = scan["id"]
    check(
        "scan has disease prediction + confidence",
        bool(scan.get("disease_name")) and 0 <= scan.get("confidence", -1) <= 1,
        str(scan.get("disease_name")),
    )

    # ── Explain (Grad-CAM) ─────────────────────────────────────────────────
    r = client.get(f"/scans/{scan_pk}/explain", headers=headers)
    explain = r.json() if r.status_code == 200 else {}
    check(
        "GET /scans/{id}/explain",
        r.status_code == 200 and bool(explain.get("top5")),
        r.text[:200],
    )

    # ── Recommendations (treatment) ────────────────────────────────────────
    r = client.get(f"/scans/{scan_pk}/recommendations", headers=headers)
    rec = r.json() if r.status_code == 200 else {}
    check(
        "GET /scans/{id}/recommendations",
        r.status_code == 200 and rec.get("disease", {}).get("name"),
        r.text[:200],
    )

    # ── Soil recommendations ───────────────────────────────────────────────
    r = client.get(f"/scans/{scan_pk}/soil-recommendations", headers=headers)
    soil = r.json() if r.status_code == 200 else {}
    check(
        "GET /scans/{id}/soil-recommendations",
        r.status_code == 200 and soil.get("soil_health", {}).get("score") is not None,
        r.text[:200],
    )

    # ── Recovery tracker + log ─────────────────────────────────────────────
    r = client.get(f"/scans/{scan_pk}/recovery", headers=headers)
    tracker = r.json() if r.status_code == 200 else {}
    check(
        "GET /scans/{id}/recovery",
        r.status_code == 200 and tracker.get("scan", {}).get("id") == scan_pk,
        r.text[:200],
    )
    r = client.post(
        f"/scans/{scan_pk}/recovery/logs",
        json={"treatment_applied": "Neem oil spray", "progress": "improving"},
        headers=headers,
    )
    check(
        "POST /scans/{id}/recovery/logs",
        r.status_code in (200, 201),
        f"{r.status_code}: {r.text[:200]}",
    )
    r = client.get(f"/scans/{scan_pk}/recovery", headers=headers)
    check(
        "recovery tracker reflects the log",
        r.status_code == 200 and r.json()["total_treatments"] >= 1,
        r.text[:200],
    )

    # ── Calendar: crops → schedule → dashboard ─────────────────────────────
    r = client.get("/calendar/crops", headers=headers)
    cal_crops = r.json()["items"] if r.status_code == 200 and "items" in r.json() else r.json()
    check("GET /calendar/crops", r.status_code == 200 and len(cal_crops) > 0, r.text[:200])

    r = client.post(
        f"/calendar/crops/{crop_id}/schedule",
        json={"planting_date": date.today().isoformat()},
        headers=headers,
    )
    check(
        "POST /calendar/crops/{id}/schedule",
        r.status_code == 201,
        f"{r.status_code}: {r.text[:200]}",
    )

    r = client.get("/calendar", headers=headers)
    dashboard = r.json() if r.status_code == 200 else {}
    schedules = dashboard.get("schedules", [])
    check(
        "GET /calendar dashboard has schedules + tasks",
        r.status_code == 200 and len(schedules) >= 1 and sum(s["total"] for s in schedules) >= 1,
        r.text[:200],
    )

    # ── Voice assistant (en + hi) ──────────────────────────────────────────
    r = client.post(
        "/assistant",
        json={"query": "How do I treat the disease on my crop?", "lang": "en"},
        headers=headers,
    )
    en = r.json() if r.status_code == 200 else {}
    check(
        "POST /assistant (en treatment)",
        r.status_code == 200 and en.get("intent") == "treatment" and en.get("sections"),
        f"{r.status_code}: {r.text[:200]}",
    )
    r = client.post("/assistant", json={"query": "आज के काम क्या हैं?"}, headers=headers)
    hi = r.json() if r.status_code == 200 else {}
    check(
        "POST /assistant (hi auto-detect + calendar)",
        r.status_code == 200
        and hi.get("lang") == "hi"
        and hi.get("intent") in ("calendar", "help"),
        f"{r.status_code}: {r.text[:200]}",
    )

    # ── History ────────────────────────────────────────────────────────────
    r = client.get("/scans", headers=headers)
    hist = r.json() if r.status_code == 200 else {}
    check(
        "GET /scans history",
        r.status_code == 200 and len(hist.get("items", [])) >= 1,
        r.text[:200],
    )

    # ── Profile ────────────────────────────────────────────────────────────
    r = client.patch("/users/me", json={"name": "Smoke Tester Jr"}, headers=headers)
    check(
        "PATCH /users/me",
        r.status_code == 200 and r.json()["name"] == "Smoke Tester Jr",
        r.text[:200],
    )

    # ── Sessions / devices ─────────────────────────────────────────────────
    r = client.get("/auth/sessions", headers=headers)
    check("GET /auth/sessions", r.status_code == 200, r.text[:200])
    r = client.get("/auth/devices", headers=headers)
    check("GET /auth/devices", r.status_code == 200, r.text[:200])

    # ── Offline sync ───────────────────────────────────────────────────────
    _buf = io.BytesIO()
    Image.new("RGB", (224, 224), (10, 120, 90)).save(_buf, format="JPEG")
    r = client.post(
        "/scans/sync",
        json=[
            {
                "client_scan_id": str(uuid.uuid4()),
                "images": [
                    {
                        "content_type": "image/jpeg",
                        "data": base64.b64encode(_buf.getvalue()).decode(),
                        "filename": "leaf.jpg",
                    }
                ],
                "crop_id": crop_id,
                "part_type": "leaf",
            }
        ],
        headers=headers,
    )
    check("POST /scans/sync", r.status_code == 200, f"{r.status_code}: {r.text[:200]}")

    print(f"\nJourney complete: {len(passed)} passed, {len(failed)} failed")
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
