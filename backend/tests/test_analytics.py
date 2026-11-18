"""Farmer-scoped analytics aggregation and CSV export tests."""

import uuid
from datetime import UTC, datetime

from app.db.session import async_session_factory
from app.models.calendar import CalendarTask, CropSchedule
from app.models.catalog import Crop
from app.models.harvest import HarvestRecord
from app.models.recovery import RecoveryLog
from app.models.scan import Scan
from app.models.scheme import GovernmentScheme, SchemeUsageEvent
from app.models.yield_estimate import YieldEstimateRecord


async def _register(client, phone: str) -> tuple[int, dict[str, str]]:
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "phone": phone,
            "name": "Analytics Tester",
            "role": "farmer",
            "password": "secret123",
        },
    )
    assert response.status_code == 201, response.text
    headers = {"Authorization": f"Bearer {response.json()['access_token']}"}
    me = await client.get("/api/v1/auth/me", headers=headers)
    return int(me.json()["id"]), headers


async def test_analytics_aggregates_only_current_users_records_and_exports_csv(client):
    user_id, headers = await _register(client, "+919300000001")
    other_user_id, _ = await _register(client, "+919300000002")
    now = datetime.now(UTC)
    today = now.date()
    async with async_session_factory() as db:
        crop = Crop(name="analytics-tomato", common_name="Analytics Tomato", growth_days=90)
        db.add(crop)
        await db.flush()
        schedule = CropSchedule(
            user_id=user_id,
            crop_id=crop.id,
            planting_date=today,
        )
        other_schedule = CropSchedule(
            user_id=other_user_id,
            crop_id=crop.id,
            planting_date=today,
        )
        db.add_all([schedule, other_schedule])
        await db.flush()
        scan = Scan(
            client_scan_id=str(uuid.uuid4()),
            user_id=user_id,
            media_items=[],
            image_path="test.jpg",
            crop_id=crop.id,
            disease_name="Leaf spot",
            confidence=0.9,
            severity="moderate",
            provider="test",
            model_version="test",
            ai_metadata={},
        )
        other_scan = Scan(
            client_scan_id=str(uuid.uuid4()),
            user_id=other_user_id,
            media_items=[],
            image_path="other.jpg",
            crop_id=crop.id,
            disease_name="Other user's disease",
            confidence=0.9,
            severity="severe",
            provider="test",
            model_version="test",
            ai_metadata={},
        )
        formula_scan = Scan(
            client_scan_id=str(uuid.uuid4()),
            user_id=user_id,
            media_items=[],
            image_path="formula.jpg",
            crop_id=crop.id,
            disease_name="\t=1+1",
            confidence=0.8,
            provider="test",
            model_version="test",
            ai_metadata={},
        )
        db.add_all([scan, other_scan, formula_scan])
        scheme = GovernmentScheme(
            name="Analytics source record",
            category="test",
            description="Test data only",
            state_codes=[],
            crops=[],
            farmer_categories=[],
            eligibility_requirements=[],
            eligibility_rules={},
            required_documents=[],
            source_name="Test source",
            source_url="https://example.gov/test",
            is_verified=False,
            is_active=True,
        )
        db.add(scheme)
        await db.flush()
        db.add_all(
            [
                RecoveryLog(
                    scan_id=scan.id,
                    user_id=user_id,
                    treatment_applied="Recorded treatment",
                    progress="improving",
                    applied_at=now,
                ),
                RecoveryLog(
                    scan_id=other_scan.id,
                    user_id=user_id,
                    treatment_applied="Inconsistent cross-owner record",
                    progress="worsening",
                    applied_at=now,
                ),
                CalendarTask(
                    schedule_id=schedule.id,
                    kind="watering",
                    title="Water",
                    due_at=now,
                    completed_at=now,
                ),
                HarvestRecord(
                    user_id=user_id,
                    schedule_id=schedule.id,
                    actual_yield_kg=3000,
                    area_hectares=1,
                    harvested_on=today,
                ),
                YieldEstimateRecord(
                    user_id=user_id,
                    crop_id=crop.id,
                    schedule_id=schedule.id,
                    planting_date=today,
                    area_hectares=1,
                    estimated_yield_kg=2500,
                    historical_harvest_count=3,
                    reliability="moderate",
                    created_at=now,
                ),
                SchemeUsageEvent(
                    user_id=user_id,
                    scheme_id=scheme.id,
                    action="view",
                    state_code="KA",
                    crop_name="tomato",
                    created_at=now,
                ),
                SchemeUsageEvent(
                    user_id=user_id,
                    scheme_id=scheme.id,
                    action="eligibility_check",
                    state_code="KA",
                    crop_name="tomato",
                    created_at=now,
                ),
                SchemeUsageEvent(
                    user_id=other_user_id,
                    scheme_id=scheme.id,
                    action="view",
                    state_code="KA",
                    crop_name="tomato",
                    created_at=now,
                ),
            ]
        )
        await db.commit()
        crop_id = crop.id

    report_response = await client.get(
        f"/api/v1/analytics/agriculture?period_start={today}&period_end={today}&crop_id={crop_id}",
        headers=headers,
    )
    assert report_response.status_code == 200, report_response.text
    report = report_response.json()
    assert report["actual_harvests"] == 1
    assert report["actual_yield_kg"] == 3000
    assert report["total_calendar_tasks"] == 1
    assert report["completed_calendar_tasks"] == 1
    assert {row["disease_name"] for row in report["disease_occurrences"]} == {
        "Leaf spot",
        "\t=1+1",
    }
    assert report["treatment_progress"] == [{"category": "improving", "count": 1}]
    assert "Historical weather-risk assessments are not persisted." in report["unavailable_data"]
    comparison = report["yield_comparisons"][0]
    assert comparison["estimated_yield_kg_per_hectare"] == 2500
    assert comparison["actual_yield_kg_per_hectare"] == 3000
    assert comparison["difference_kg_per_hectare"] == 500
    assert report["weather_risk_data_available"] is False

    scheme_report = await client.get(
        f"/api/v1/analytics/schemes?period_start={today}&period_end={today}&crop_name=tomato&state_code=KA",
        headers=headers,
    )
    assert scheme_report.status_code == 200, scheme_report.text
    assert scheme_report.json()["total_schemes_viewed"] == 1
    assert scheme_report.json()["eligibility_checks"] == 1
    assert scheme_report.json()["applications"] == 0
    assert scheme_report.json()["application_tracking_available"] is False
    assert scheme_report.json()["usage_trend"][0]["date"] == today.isoformat()

    export = await client.get(
        f"/api/v1/analytics/agriculture/export.csv?period_start={today}&period_end={today}",
        headers=headers,
    )
    assert export.status_code == 200
    assert export.headers["content-type"].startswith("text/csv")
    assert "Leaf spot" in export.text
    assert "unavailable_data" in export.text
    assert "Historical weather-risk assessments are not persisted." in export.text
    assert "'\t=1+1 (unspecified)" in export.text


async def test_empty_analytics_export_has_headers_and_no_fabricated_rows(client):
    _, headers = await _register(client, "+919300000004")
    response = await client.get(
        "/api/v1/analytics/agriculture/export.csv?period_start=2026-01-01&period_end=2026-01-01",
        headers=headers,
    )
    assert response.status_code == 200
    rows = response.text.splitlines()
    assert rows[0] == "metric,category,value"
    assert "actual_harvests,,0" in rows
    assert "calendar_tasks,all,0" in rows
    assert not any(row.startswith("disease_occurrence,") for row in rows)


async def test_analytics_validate_date_ranges_and_require_auth(client):
    assert (await client.get("/api/v1/analytics/agriculture")).status_code == 401
    _, headers = await _register(client, "+919300000003")
    response = await client.get(
        "/api/v1/analytics/agriculture?period_start=2026-03-02&period_end=2026-03-01",
        headers=headers,
    )
    assert response.status_code == 422
