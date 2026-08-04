"""Service-level tests for scan persistence, idempotency, history queries.

Database-backed (async SQLite via conftest fixtures). The HTTP surface —
upload, prediction, ownership at the API boundary — is covered by Task 4.4's
API integration tests.
"""

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from app.models.audit import AuditLog
from app.models.user import User
from app.schemas.scan import ScanCreate
from app.services.scans import ScanNotFoundError, ScanService
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError


def _client_id(n: int) -> str:
    return str(uuid.UUID(int=n))


def _payload(user_id: int, client_scan_id: str, **overrides) -> ScanCreate:
    values = dict(
        client_scan_id=client_scan_id,
        user_id=user_id,
        image_path=f"{user_id}/scan.jpg",
        media_items=[
            {
                "source_type": "upload",
                "path": f"{user_id}/scan.jpg",
                "part_type": "leaf",
            }
        ],
        crop_id=101,
        part_type="leaf",
        disease_id=1,
        disease_name="Late Blight",
        confidence=0.92,
        severity="Moderate",
        stage="Early",
        provider="baseline",
        model_name="rule-baseline",
        model_version="baseline-v1",
        dataset_version="v1",
        preprocessing_time_ms=12.0,
        inference_time_ms=8.0,
        processing_time_ms=25.0,
        ai_metadata={
            "rankings": [{"disease_name": "Powdery Mildew", "confidence": 0.7, "disease_id": 2}]
        },
        device_id="dev-1",
    )
    values.update(overrides)
    return ScanCreate(**values)


async def _user(db, phone: str = "+919000000001") -> User:
    user = User(role="farmer", phone=phone, name="Tester", status="active", verified=True)
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def _backdate(db, scan, days: int) -> None:
    # Store naive-UTC to match SQLite's round-trip of DateTime columns.
    scan.created_at = (datetime.now(UTC) - timedelta(days=days)).replace(tzinfo=None)
    await db.commit()


# ── Create / read / ownership ───────────────────────────────────────────


async def test_create_and_get_for_user(db):
    user = await _user(db)
    scan = await ScanService(db).create(_payload(user.id, _client_id(1)))
    fetched = await ScanService(db).get_for_user(scan.id, user.id)
    assert fetched.disease_name == "Late Blight"
    assert fetched.confidence == 0.92
    assert fetched.dataset_version == "v1"
    assert fetched.processing_time_ms == 25.0
    # Explainability prep: rankings + media preserved.
    assert fetched.rankings[0]["disease_name"] == "Powdery Mildew"
    assert fetched.media_items[0]["source_type"] == "upload"


async def test_get_for_user_rejects_other_owner(db):
    owner = await _user(db, "+919000000001")
    other = await _user(db, "+919000000002")
    scan = await ScanService(db).create(_payload(owner.id, _client_id(2)))
    with pytest.raises(ScanNotFoundError):
        await ScanService(db).get_for_user(scan.id, other.id)


async def test_find_by_client_id_idempotency_lookup(db):
    user = await _user(db)
    svc = ScanService(db)
    scan = await svc.create(_payload(user.id, _client_id(3)))
    existing = await svc.find_by_client_id(_client_id(3), user.id)
    assert existing is not None and existing.id == scan.id
    assert await svc.find_by_client_id(_client_id(99), user.id) is None


async def test_client_scan_id_is_unique(db):
    user = await _user(db)
    svc = ScanService(db)
    await svc.create(_payload(user.id, _client_id(4)))
    with pytest.raises(IntegrityError):
        await svc.create(_payload(user.id, _client_id(4)))


# ── Delete ──────────────────────────────────────────────────────────────


async def test_delete_for_user_removes_row(db):
    user = await _user(db)
    scan = await ScanService(db).create(_payload(user.id, _client_id(5)))
    await ScanService(db).delete_for_user(scan.id, user.id)
    with pytest.raises(ScanNotFoundError):
        await ScanService(db).get_for_user(scan.id, user.id)


async def test_delete_for_user_rejects_other_owner(db):
    owner = await _user(db, "+919000000001")
    other = await _user(db, "+919000000002")
    scan = await ScanService(db).create(_payload(owner.id, _client_id(6)))
    with pytest.raises(ScanNotFoundError):
        await ScanService(db).delete_for_user(scan.id, other.id)


# ── History queries (filters, search, sort, pagination) ────────────────


async def _seed_history(db, user_id: int) -> None:
    svc = ScanService(db)
    specs = [
        ("Late Blight", 101, 0.92),
        ("Powdery Mildew", 101, 0.8),
        ("Leaf Rust", 102, 0.75),
        ("Late Blight", 102, 0.88),
        ("Healthy", 101, 0.97),
    ]
    for i, (disease, crop, conf) in enumerate(specs):
        scan = await svc.create(
            _payload(
                user_id,
                _client_id(10 + i),
                disease_name=disease,
                crop_id=crop,
                confidence=conf,
            )
        )
        await _backdate(db, scan, days=i)  # 0..4 days old


async def test_list_returns_all_and_total(db):
    user = await _user(db)
    await _seed_history(db, user.id)
    rows, total = await ScanService(db).list_scans(user.id)
    assert total == 5
    assert len(rows) == 5


async def test_list_filters_by_crop(db):
    user = await _user(db)
    await _seed_history(db, user.id)
    rows, total = await ScanService(db).list_scans(user.id, crop_id=102)
    assert total == 2
    assert {r.crop_id for r in rows} == {102}


async def test_list_filters_by_disease(db):
    user = await _user(db)
    await _seed_history(db, user.id)
    rows, total = await ScanService(db).list_scans(user.id, disease="rust")
    assert total == 1
    assert rows[0].disease_name == "Leaf Rust"


async def test_list_filters_by_date_range(db):
    user = await _user(db)
    await _seed_history(db, user.id)
    cutoff = datetime.now(UTC)
    rows, total = await ScanService(db).list_scans(
        user.id, date_from=cutoff - timedelta(days=2), date_to=cutoff
    )
    assert total == 2  # the two newest (0 and 1 days old)


async def test_list_search_matches_disease_or_provider(db):
    user = await _user(db)
    await _seed_history(db, user.id)
    rows, total = await ScanService(db).list_scans(user.id, search="blight")
    assert total == 2


async def test_list_sorts_by_confidence_asc(db):
    user = await _user(db)
    await _seed_history(db, user.id)
    rows, _ = await ScanService(db).list_scans(user.id, sort="confidence", order="asc")
    confidences = [r.confidence for r in rows]
    assert confidences == sorted(confidences)


async def test_list_paginates(db):
    user = await _user(db)
    await _seed_history(db, user.id)
    page1, total = await ScanService(db).list_scans(user.id, page=1, page_size=2)
    page2, _ = await ScanService(db).list_scans(user.id, page=2, page_size=2)
    assert total == 5
    assert len(page1) == 2 and len(page2) == 2
    assert page1[0].id != page2[0].id  # no overlap


# ── Task 4.3 filters (confidence / severity / sync status) ──────────────


async def test_list_filters_by_confidence_range(db):
    user = await _user(db)
    await _seed_history(db, user.id)  # confidences 0.92, 0.8, 0.75, 0.88, 0.97
    rows, total = await ScanService(db).list_scans(user.id, confidence_min=0.85)
    assert total == 3  # 0.92, 0.88, 0.97
    rows, total = await ScanService(db).list_scans(user.id, confidence_max=0.8)
    assert total == 2  # 0.80, 0.75
    assert all(r.confidence <= 0.8 for r in rows)


async def test_list_filters_by_severity(db):
    user = await _user(db)
    await ScanService(db).create(_payload(user.id, _client_id(25), severity="low"))
    await ScanService(db).create(_payload(user.id, _client_id(26), severity="severe"))
    rows, total = await ScanService(db).list_scans(user.id, severity="severe")
    assert total == 1
    assert rows[0].severity == "severe"


async def test_list_filters_by_sync_status(db):
    user = await _user(db)
    svc = ScanService(db)
    await svc.create(_payload(user.id, _client_id(27)))  # default synced
    pending = await svc.create(_payload(user.id, _client_id(28)))
    pending.sync_status = "pending"  # ScanCreate has no sync_status; set directly
    await db.commit()
    rows, total = await svc.list_scans(user.id, sync_status="pending")
    assert total == 1
    assert rows[0].sync_status == "pending"


# ── Soft delete + audit ─────────────────────────────────────────────────


async def test_soft_delete_hides_from_history_and_lookup(db):
    user = await _user(db)
    svc = ScanService(db)
    scan = await svc.create(_payload(user.id, _client_id(29)))
    await svc.delete_for_user(scan.id, user.id)

    with pytest.raises(ScanNotFoundError):
        await svc.get_for_user(scan.id, user.id)
    rows, total = await svc.list_scans(user.id)
    assert total == 0
    # A deleted scan must never resurface via the offline idempotency lookup.
    assert await svc.find_by_client_id(scan.client_scan_id, user.id) is None


async def test_soft_delete_writes_audit_log(db):
    user = await _user(db)
    svc = ScanService(db)
    scan = await svc.create(_payload(user.id, _client_id(30)))
    await svc.delete_for_user(scan.id, user.id)

    entry = await db.scalar(select(AuditLog).where(AuditLog.resource_id == str(scan.id)))
    assert entry is not None
    assert entry.action == "scan.delete"
    assert entry.resource_type == "scan"
    assert entry.actor_id == user.id
    assert entry.details["client_scan_id"] == scan.client_scan_id


# ── Admin access ────────────────────────────────────────────────────────


async def test_admin_flag_reads_any_scan(db):
    owner = await _user(db, "+919000000001")
    other = await _user(db, "+919000000002")
    svc = ScanService(db)
    scan = await svc.create(_payload(owner.id, _client_id(31)))

    assert (await svc.get_for_user(scan.id, other.id, admin=True)).id == scan.id
    with pytest.raises(ScanNotFoundError):
        await svc.get_for_user(scan.id, other.id)  # non-admin blocked


async def test_admin_lists_all_users_scans(db):
    u1 = await _user(db, "+919000000001")
    u2 = await _user(db, "+919000000002")
    svc = ScanService(db)
    await svc.create(_payload(u1.id, _client_id(32)))
    await svc.create(_payload(u2.id, _client_id(33)))
    rows, total = await svc.list_scans(None)
    assert total == 2
    assert {r.user_id for r in rows} == {u1.id, u2.id}
