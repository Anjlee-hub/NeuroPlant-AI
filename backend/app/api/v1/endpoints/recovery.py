"""Crop recovery tracker endpoints (M3, Task 4).

The tracker is nested under scans (``/scans/{scan_id}/recovery``) so it inherits
the exact same ownership guard as the other scan sub-resources: ``404`` for a
missing / soft-deleted / other-user's scan, then ``404`` when a log id doesn't
belong to that scan. The service owns the recovery policy (percentage / status /
risk); these handlers only map HTTP semantics.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_current_user
from app.db.session import get_db
from app.models.base import UserRole
from app.models.user import User
from app.schemas.recovery import (
    RecoveryLogIn,
    RecoveryLogOut,
    RecoveryLogUpdate,
    RecoveryTrackerOut,
)
from app.services.recovery import RecoveryTrackerService
from app.services.scans import ScanService

router = APIRouter(prefix="/scans", tags=["scans", "recovery"])

Db = Annotated[AsyncSession, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]


@router.get("/{scan_id}/recovery", response_model=RecoveryTrackerOut)
async def get_recovery_tracker(scan_id: int, user: CurrentUser, db: Db) -> RecoveryTrackerOut:
    """Full recovery section for one scan: computed percentage/status/risk +
    the applied-ordered timeline of treatment logs.

    Same ownership guard as detail (``404`` for missing / soft-deleted /
    other-user's scans). Reading the tracker never mutates anything.
    """
    scan = await ScanService(db).get_for_user(scan_id, user.id, admin=user.role == UserRole.ADMIN)
    return await RecoveryTrackerService(db).tracker(scan)


@router.post(
    "/{scan_id}/recovery/logs",
    response_model=RecoveryLogOut,
    status_code=status.HTTP_201_CREATED,
)
async def add_recovery_log(
    scan_id: int, payload: RecoveryLogIn, user: CurrentUser, db: Db
) -> RecoveryLogOut:
    """Record one treatment action the farmer applied against this scan.

    ``applied_at`` defaults to now when omitted. The next ``GET /recovery``
    reflects the new log in the percentage, status and timeline.
    """
    scan = await ScanService(db).get_for_user(scan_id, user.id, admin=user.role == UserRole.ADMIN)
    return await RecoveryTrackerService(db).add_log(scan, payload)


@router.patch(
    "/{scan_id}/recovery/logs/{log_id}", response_model=RecoveryLogOut
)
async def update_recovery_log(
    scan_id: int, log_id: int, payload: RecoveryLogUpdate, user: CurrentUser, db: Db
) -> RecoveryLogOut:
    """Partially edit one of the scan's treatment logs.

    Only the fields sent are changed; ``404`` when the log isn't on this scan.
    """
    scan = await ScanService(db).get_for_user(scan_id, user.id, admin=user.role == UserRole.ADMIN)
    return await RecoveryTrackerService(db).update_log(scan, log_id, payload)


@router.delete(
    "/{scan_id}/recovery/logs/{log_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_recovery_log(scan_id: int, log_id: int, user: CurrentUser, db: Db) -> None:
    """Remove one of the scan's treatment logs.

    ``204`` on success; ``404`` for a log that isn't on this scan (or a scan the
    user can't see).
    """
    scan = await ScanService(db).get_for_user(scan_id, user.id, admin=user.role == UserRole.ADMIN)
    await RecoveryTrackerService(db).delete_log(scan, log_id)
