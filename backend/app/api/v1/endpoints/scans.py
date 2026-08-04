"""Scan endpoints — upload photos and run AI disease detection (M2, Task 4.2).

``POST /scans`` accepts multipart form data (one or more images + form fields).
The pipeline service does the real work; this module only maps the multipart
payload and the HTTP status semantics (201 created, 200 idempotent replay of an
already-known ``client_scan_id``).
"""

from __future__ import annotations

import re
from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Response,
    UploadFile,
    status,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.preprocess import get_preprocessor
from app.api.v1.deps import (
    get_current_user,
    get_detection_service,
    scan_upload_rate_limit,
)
from app.core.config import get_settings
from app.db.session import get_db
from app.models.scan import Scan
from app.models.user import User
from app.schemas.scan import CLIENT_SCAN_ID_PATTERN, PART_TYPES, ScanOut
from app.services.detection import DetectionService
from app.services.scan_pipeline import ScanPipelineService
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
