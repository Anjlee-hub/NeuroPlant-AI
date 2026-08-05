"""API tests for GET /scans/{id}/explain (M2, Task 5.3).

Covers the explainability payload contract: heatmap + overlay URLs, the
plain-language explanation, top-5 candidates, confidence band + expert advice,
Grad-CAM provenance and model metadata — plus ownership 404s and graceful
degradation when a scan has no heatmap.
"""

import uuid
from io import BytesIO

from app.db.seed import seed_catalog
from app.models.user import User
from app.schemas.scan import ScanCreate
from app.services.scans import ScanService
from PIL import Image
from sqlalchemy import select


def _client_id(n: int) -> str:
    return str(uuid.UUID(int=n))


def _jpeg_bytes() -> bytes:
    buf = BytesIO()
    Image.new("RGB", (224, 224), (120, 90, 60)).save(buf, format="JPEG")
    return buf.getvalue()


async def _auth_headers(client, phone: str) -> dict:
    resp = await client.post(
        "/api/v1/auth/register",
        json={"phone": phone, "name": "Tester", "role": "farmer", "password": "secret123"},
    )
    assert resp.status_code == 201, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


async def _user_id(db, phone: str) -> int:
    user = await db.scalar(select(User).where(User.phone == phone))
    assert user is not None
    return user.id


async def _upload(client, headers, *, client_scan_id: str) -> dict:
    resp = await client.post(
        "/api/v1/scans",
        files=[("files", ("leaf.jpg", _jpeg_bytes(), "image/jpeg"))],
        data={"client_scan_id": client_scan_id},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


async def _seed_scan(db, user_id: int, *, confidence: float = 0.6) -> int:
    """Insert a scan directly (bypassing the pipeline) for degrade-path tests."""
    ai_metadata = {
        "rankings": [{"disease_name": "Powdery Mildew", "confidence": 0.55, "disease_id": 2}],
        "top5": [
            {
                "disease_name": "Late Blight",
                "confidence": confidence,
                "disease_id": 1,
                "crop_id": 101,
            },
            {
                "disease_name": "Powdery Mildew",
                "confidence": 0.55,
                "disease_id": 2,
                "crop_id": 101,
            },
        ],
        "confidence": {"top": confidence, "level": "medium"},
        "model": {"provider": "baseline", "model_name": "rule-baseline"},
    }
    scan = await ScanService(db).create(
        ScanCreate(
            client_scan_id=_client_id(40),
            user_id=user_id,
            image_path=f"{user_id}/scans/leaf.jpg",
            media_items=[
                {
                    "source_type": "upload",
                    "path": f"{user_id}/scans/leaf.jpg",
                    "part_type": "leaf",
                }
            ],
            processed_image_path=f"{user_id}/processed/leaf.jpg",
            crop_id=101,
            part_type="leaf",
            disease_id=1,
            disease_name="Late Blight",
            confidence=confidence,
            severity="moderate",
            stage="early",
            provider="baseline",
            model_name="rule-baseline",
            model_version="baseline-v1",
            dataset_version="v1",
            ai_metadata=ai_metadata,
        )
    )
    return scan.id


# ── Happy path (real upload → full payload) ─────────────────────────────


async def test_explain_returns_full_payload(client, db):
    await seed_catalog(db)
    headers = await _auth_headers(client, "+919000000011")
    scan = await _upload(client, headers, client_scan_id=_client_id(2))

    resp = await client.get(f"/api/v1/scans/{scan['id']}/explain", headers=headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()

    assert body["scan_id"] == scan["id"]
    assert body["disease"]["name"] == scan["disease_name"]
    assert body["disease"]["severity"] == scan["severity"]
    assert body["disease"]["stage"] == scan["stage"]
    assert isinstance(body["disease"]["symptoms"], list)

    assert body["confidence"]["top"] == scan["confidence"]
    assert body["confidence"]["level"] in {"high", "medium", "low"}
    assert body["confidence"]["advice"]

    assert body["top5"], "top-5 candidates must be present"
    assert body["top5"][0]["disease_name"] == scan["disease_name"]

    assert body["heatmap"] is not None
    assert body["heatmap"]["provider"] == "baseline"
    assert body["heatmap"]["class_name"] == scan["disease_name"]
    assert body["heatmap"]["time_ms"] > 0

    assert body["heatmap_url"].startswith("/media/")
    assert body["overlay_url"].startswith("/media/")

    assert scan["disease_name"] in body["explanation"]
    assert body["model"]["provider"] == "baseline"

    # Pipeline + Grad-CAM timing (Task 5.4) — captured at prediction time. The
    # rule-baseline classifier is sub-millisecond, so assert shape + internal
    # consistency rather than absolute positive latencies (those are pinned
    # exactly by the ExplainService unit tests).
    assert body["timing"]["preprocessing_time_ms"] >= 0
    assert body["timing"]["inference_time_ms"] >= 0
    assert body["timing"]["processing_time_ms"] >= body["timing"]["inference_time_ms"]
    assert body["timing"]["heatmap_time_ms"] == body["heatmap"]["time_ms"]
    assert body["model"]["model_version"] == scan["model_version"]
    assert body["model"]["dataset_version"] == scan["dataset_version"]


# ── Ownership / existence guards ─────────────────────────────────────────


async def test_explain_404_for_other_users_scan(client, db):
    await seed_catalog(db)
    owner = await _auth_headers(client, "+919000000012")
    other = await _auth_headers(client, "+919000000013")
    scan = await _upload(client, owner, client_scan_id=_client_id(3))

    resp = await client.get(f"/api/v1/scans/{scan['id']}/explain", headers=other)
    assert resp.status_code == 404


async def test_explain_404_for_missing_scan(client, db):
    await seed_catalog(db)
    headers = await _auth_headers(client, "+919000000014")
    resp = await client.get("/api/v1/scans/999999/explain", headers=headers)
    assert resp.status_code == 404


# ── Degradation without a heatmap ────────────────────────────────────────


async def test_explain_degrades_without_heatmap(client, db):
    await seed_catalog(db)
    headers = await _auth_headers(client, "+919000000015")
    scan_id = await _seed_scan(db, await _user_id(db, "+919000000015"))

    resp = await client.get(f"/api/v1/scans/{scan_id}/explain", headers=headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["heatmap"] is None
    assert body["heatmap_url"] is None
    assert body["overlay_url"] is None
    assert body["timing"]["heatmap_time_ms"] is None
    assert "Late Blight" in body["explanation"]
    assert body["confidence"]["level"] == "medium"
    assert body["confidence"]["advice"]


async def test_explain_low_confidence_carries_advice(client, db):
    await seed_catalog(db)
    headers = await _auth_headers(client, "+919000000016")
    scan_id = await _seed_scan(db, await _user_id(db, "+919000000016"), confidence=0.4)

    resp = await client.get(f"/api/v1/scans/{scan_id}/explain", headers=headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["confidence"]["level"] == "low"
    advice = body["confidence"]["advice"].lower()
    assert "retake" in advice or "agronomist" in advice
