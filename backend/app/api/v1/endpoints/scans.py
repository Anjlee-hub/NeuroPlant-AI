"""Scan endpoints — upload photos and run AI disease detection (M2, Task 4.2).

``POST /scans`` accepts multipart form data (one or more images + form fields)
and ``POST /scans/sync`` accepts a JSON batch of base64 offline scans (Task 6).
Both delegate to the shared pipeline service; this module only maps the raw
payloads and the HTTP status semantics (201 created / 200 idempotent replay for
uploads; per-item ``created | replayed | failed`` results for sync).
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    Response,
    UploadFile,
    status,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.preprocess import get_preprocessor
from app.api.v1.deps import (
    get_current_user,
    get_detection_service,
    scan_sync_rate_limit,
    scan_upload_rate_limit,
)
from app.core.config import get_settings
from app.db.session import get_db
from app.models.base import UserRole
from app.models.scan import Scan
from app.models.user import User
from app.schemas.recommendation import DiseaseRecommendationOut
from app.schemas.scan import (
    CLIENT_SCAN_ID_PATTERN,
    PART_TYPES,
    ScanExplainOut,
    ScanListOut,
    ScanOut,
    ScanSyncItemIn,
    ScanSyncOut,
    ScanSyncResultOut,
    SyncErrorOut,
)
from app.schemas.soil import SoilRecommendationOut
from app.services.detection import DetectionService
from app.services.explain import ExplainService
from app.services.recommendations import RecommendationService
from app.services.scan_pipeline import ScanPipelineError, ScanPipelineService
from app.services.scans import ScanService
from app.services.soil import SoilRecommendationService
from app.services.storage import get_storage_service

router = APIRouter(prefix="/scans", tags=["scans"])

Db = Annotated[AsyncSession, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]
Detection = Annotated[DetectionService, Depends(get_detection_service)]


@router.post("", response_model=ScanOut, status_code=status.HTTP_201_CREATED)
async def create_scan(
    response: Response,
    files: Annotated[
        list[UploadFile],
        File(description="Leaf/fruit/stem/plant photos (JPEG/PNG/WebP)"),
    ],
    client_scan_id: Annotated[
        str,
        Form(description="Client-generated UUID; offline idempotency key"),
    ],
    user: CurrentUser,
    db: Db,
    detection: Detection,
    _rate: None = Depends(scan_upload_rate_limit),
    crop_id: Annotated[int | None, Form()] = None,
    part_type: Annotated[str | None, Form()] = None,
    device_id: Annotated[str | None, Form()] = None,
) -> Scan:
    """Upload one or more images and run disease detection on them.

    Returns ``201`` with the persisted scan, or ``200`` with the previously
    stored scan when ``client_scan_id`` was already seen (idempotent retry).
    """
    if not re.fullmatch(CLIENT_SCAN_ID_PATTERN, client_scan_id):
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "code": "invalid_client_scan_id",
                "message": "client_scan_id must be a UUID",
            },
        )
    if part_type is not None and part_type not in PART_TYPES:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "code": "invalid_part_type",
                "message": f"part_type must be one of: {', '.join(PART_TYPES)}",
            },
        )

    settings = get_settings()
    pipeline = ScanPipelineService(
        db,
        detection,
        get_storage_service(),
        get_preprocessor("default"),
        max_images=settings.scan_max_images,
        timeout_seconds=settings.scan_inference_timeout_seconds,
    )
    scan, created = await pipeline.process_upload(
        user_id=user.id,
        files=files,
        client_scan_id=client_scan_id,
        crop_id=crop_id,
        part_type=part_type,
        device_id=device_id,
    )
    if not created:
        response.status_code = status.HTTP_200_OK
    return scan


@router.post("/sync", response_model=ScanSyncOut, status_code=status.HTTP_200_OK)
async def sync_offline_scans(
    payload: list[ScanSyncItemIn],
    user: CurrentUser,
    db: Db,
    detection: Detection,
    _rate: None = Depends(scan_sync_rate_limit),
) -> ScanSyncOut:
    """Reconcile a batch of queued offline scans (Task 6).

    Accepts a JSON array of :class:`ScanSyncItemIn`; each item is processed
    independently through the exact same pipeline as a live upload, so one
    item's failure never blocks the rest. Idempotency is per
    ``client_scan_id`` — already-persisted ids come back ``replayed`` with
    their existing authoritative row, new ids ``created``, and failures
    ``failed`` with a machine-readable error. Each item commits in its own
    transaction, so a batch is never half-applied.
    """
    if not payload:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={"code": "empty_batch", "message": "sync batch must not be empty"},
        )
    settings = get_settings()
    if len(payload) > settings.scan_sync_max_items:
        raise HTTPException(
            status.HTTP_413_CONTENT_TOO_LARGE,
            detail={
                "code": "batch_too_large",
                "message": f"sync batch exceeds the limit of {settings.scan_sync_max_items} items",
            },
        )

    pipeline = ScanPipelineService(
        db,
        detection,
        get_storage_service(),
        get_preprocessor("default"),
        max_images=settings.scan_max_images,
        timeout_seconds=settings.scan_inference_timeout_seconds,
    )
    scans = ScanService(db)
    # One batch-wide idempotency query; replays are short-circuited here so
    # already-synced items never re-enter the detection pipeline.
    existing = await scans.find_by_client_ids([item.client_scan_id for item in payload], user.id)

    results: list[ScanSyncResultOut] = []
    created = replayed = failed = 0
    for item in payload:
        prior = existing.get(item.client_scan_id)
        if prior is not None:
            replayed += 1
            results.append(
                ScanSyncResultOut(client_scan_id=item.client_scan_id, status="replayed", scan=prior)
            )
            continue
        try:
            scan, is_created = await pipeline.process_sync_item(user_id=user.id, item=item)
        except ScanPipelineError as exc:
            failed += 1
            results.append(
                ScanSyncResultOut(
                    client_scan_id=item.client_scan_id,
                    status="failed",
                    error=SyncErrorOut(code=exc.code, message=str(exc)),
                )
            )
            continue
        if is_created:
            created += 1
        else:
            replayed += 1
        results.append(
            ScanSyncResultOut(
                client_scan_id=item.client_scan_id,
                status="created" if is_created else "replayed",
                scan=scan,
            )
        )

    return ScanSyncOut(
        results=results, total=len(payload), created=created, replayed=replayed, failed=failed
    )


# ── History ──────────────────────────────────────────────────────────────


@router.get("", response_model=ScanListOut)
async def list_my_scans(
    user: CurrentUser,
    db: Db,
    page: Annotated[int, Query(ge=1, description="1-based page number")] = 1,
    page_size: Annotated[int, Query(ge=1, le=100, description="Rows per page")] = 20,
    sort: Annotated[
        str,
        Query(pattern="^(created_at|confidence|disease_name)$"),
    ] = "created_at",
    order: Annotated[str, Query(pattern="^(asc|desc)$")] = "desc",
    search: Annotated[str | None, Query(description="Free-text over disease/provider")] = None,
    crop_id: Annotated[int | None, Query(description="Filter by crop id")] = None,
    disease: Annotated[str | None, Query(description="Partial disease-name match")] = None,
    part_type: Annotated[str | None, Query(pattern="^(leaf|fruit|stem|plant|whole)$")] = None,
    date_from: Annotated[
        datetime | None, Query(description="Inclusive lower bound (ISO-8601)")
    ] = None,
    date_to: Annotated[
        datetime | None, Query(description="Inclusive upper bound (ISO-8601)")
    ] = None,
    confidence_min: Annotated[float | None, Query(ge=0.0, le=1.0)] = None,
    confidence_max: Annotated[float | None, Query(ge=0.0, le=1.0)] = None,
    severity: Annotated[str | None, Query(pattern="^(low|moderate|severe)$")] = None,
    sync_status: Annotated[
        str | None, Query(description="Sync/offline state (synced|pending|failed)")
    ] = None,
    owner_id: Annotated[int | None, Query(description="Admin-only: narrow to one user")] = None,
) -> ScanListOut:
    """Paginated, filterable, searchable scan history.

    Regular users see only their own scans (``owner_id`` is ignored for them);
    admins see every live scan and may narrow by ``owner_id``. Soft-deleted
    scans never appear.
    """
    if (
        confidence_min is not None
        and confidence_max is not None
        and confidence_min > confidence_max
    ):
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "code": "invalid_confidence_range",
                "message": "confidence_min must not exceed confidence_max",
            },
        )

    target_user = owner_id if user.role == UserRole.ADMIN else user.id
    rows, total = await ScanService(db).list_scans(
        target_user,
        crop_id=crop_id,
        disease=disease,
        part_type=part_type,
        date_from=date_from,
        date_to=date_to,
        search=search,
        confidence_min=confidence_min,
        confidence_max=confidence_max,
        severity=severity,
        sync_status=sync_status,
        sort=sort,
        order=order,
        page=page,
        page_size=page_size,
    )
    return ScanListOut(
        items=rows,
        total=total,
        page=page,
        page_size=page_size,
        has_next=page * page_size < total,
    )


@router.get("/{scan_id}", response_model=ScanOut)
async def get_scan(scan_id: int, user: CurrentUser, db: Db) -> Scan:
    """Complete details for one scan.

    Returns ``404`` for a missing, soft-deleted, or other-user's scan — the
    response is identical in every case so no scan's existence is revealed.
    """
    return await ScanService(db).get_for_user(scan_id, user.id, admin=user.role == UserRole.ADMIN)


@router.get("/{scan_id}/explain", response_model=ScanExplainOut)
async def explain_scan(scan_id: int, user: CurrentUser, db: Db) -> ScanExplainOut:
    """Grad-CAM heatmap + overlay, plain-language explanation, top-5 + metadata.

    Same ownership guard as detail: ``404`` for missing / soft-deleted /
    other-user's scans. Reads only what was captured at prediction time
    (Task 5.2) — no re-inference. A scan without a heatmap still explains the
    diagnosis, with the heatmap fields ``None``.
    """
    scan = await ScanService(db).get_for_user(scan_id, user.id, admin=user.role == UserRole.ADMIN)
    return await ExplainService(db, get_storage_service()).build(scan)


@router.get("/{scan_id}/recommendations", response_model=DiseaseRecommendationOut)
async def scan_recommendations(scan_id: int, user: CurrentUser, db: Db) -> DiseaseRecommendationOut:
    """Full treatment plan for the disease this scan predicted (M3, Task 1).

    Same ownership guard as detail (``404`` for missing / soft-deleted /
    other-user's scans), then ``404`` when the predicted disease has no plan in
    the active catalog. Reads the seeded catalog only — no hardcoded advice.
    """
    scan = await ScanService(db).get_for_user(scan_id, user.id, admin=user.role == UserRole.ADMIN)
    return await RecommendationService(db).for_scan(scan)


@router.get("/{scan_id}/soil-recommendations", response_model=SoilRecommendationOut)
async def scan_soil_recommendations(
    scan_id: int, user: CurrentUser, db: Db
) -> SoilRecommendationOut:
    """Disease-aware soil plan for the disease this scan predicted (M3, Task 3).

    Same ownership guard as detail (``404`` for missing / soft-deleted /
    other-user's scans), then ``404`` when the predicted disease has no soil plan
    in the active catalog. The advice and the soil-health score adapt to the
    scan's own severity + confidence — no hardcoded advice in controllers.
    """
    scan = await ScanService(db).get_for_user(scan_id, user.id, admin=user.role == UserRole.ADMIN)
    return await SoilRecommendationService(db).for_scan(scan)


@router.delete("/{scan_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_scan(scan_id: int, user: CurrentUser, db: Db) -> None:
    """Soft-delete a scan (kept for audit; excluded from history/sync).

    ``204`` on success; ``404`` when the scan is missing, already deleted, or
    owned by someone else; ``401`` when unauthenticated.
    """
    await ScanService(db).delete_for_user(scan_id, user.id, admin=user.role == UserRole.ADMIN)
