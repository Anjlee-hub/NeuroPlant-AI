"""Scan service — persistence and history queries.

Owns the :class:`Scan` row lifecycle (create / get / list / delete) plus the
offline idempotency lookup. The detection run itself lives in
:class:`DetectionService` (Task 2); the API endpoint composes the two.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import ColumnElement

from app.core.logging import get_logger
from app.models.audit import AuditLog
from app.models.scan import Scan
from app.schemas.scan import ScanCreate

logger = get_logger(__name__)

# Sortable columns — whitelist only, never order by client input directly.
_SORT_COLUMNS: dict[str, Any] = {
    "created_at": Scan.created_at,
    "confidence": Scan.confidence,
    "disease_name": Scan.disease_name,
}


class ScanNotFoundError(Exception):
    """The requested scan does not exist for this user."""


def _naive_utc(dt: datetime) -> datetime:
    """Normalize a filter bound to naive-UTC (SQLite stores naive UTC)."""
    if dt.tzinfo is None:
        return dt
    return dt.astimezone(UTC).replace(tzinfo=None)


def _now_naive_utc() -> datetime:
    """Current wall-clock as naive-UTC (soft-delete marker)."""
    return datetime.now(UTC).replace(tzinfo=None)


class ScanService:
    """All Scan persistence/querying behind one dependency-injectable class."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ── Read ──────────────────────────────────────────────────────────

    async def get_for_user(self, scan_id: int, user_id: int, *, admin: bool = False) -> Scan:
        """Ownership-guarded detail lookup (``admin`` bypasses the owner check).

        Missing rows and other users' rows raise the *same* error so a 404 never
        reveals whether a scan exists (ID-enumeration guard). Soft-deleted rows
        are treated as missing.
        """
        row = await self.db.get(Scan, scan_id)
        if row is None or row.deleted_at is not None:
            raise ScanNotFoundError(f"scan {scan_id} not found for user {user_id}")
        if not admin and row.user_id != user_id:
            raise ScanNotFoundError(f"scan {scan_id} not found for user {user_id}")
        return row

    async def find_by_client_id(self, client_scan_id: str, user_id: int) -> Scan | None:
        """Idempotency lookup used by the offline-sync path (Task 6)."""
        return await self.db.scalar(
            select(Scan).where(
                Scan.client_scan_id == client_scan_id,
                Scan.user_id == user_id,
                Scan.deleted_at.is_(None),
            )
        )

    async def list_scans(
        self,
        user_id: int | None,
        *,
        crop_id: int | None = None,
        disease: str | None = None,
        part_type: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        search: str | None = None,
        confidence_min: float | None = None,
        confidence_max: float | None = None,
        severity: str | None = None,
        sync_status: str | None = None,
        sort: str = "created_at",
        order: str = "desc",
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Scan], int]:
        """Paginated, filtered history. Returns ``(rows, total_count)``.

        ``user_id=None`` (admin) lists every live scan; otherwise only the given
        user's. All soft-deleted rows are excluded. A single SELECT + COUNT is
        used (Scan's JSON lists are columns, not relationships) so there are no
        N+1 queries.
        """
        conditions: list[ColumnElement[bool]] = [Scan.deleted_at.is_(None)]
        if user_id is not None:
            conditions.append(Scan.user_id == user_id)
        if crop_id is not None:
            conditions.append(Scan.crop_id == crop_id)
        if disease:
            conditions.append(Scan.disease_name.ilike(f"%{disease}%"))
        if part_type:
            conditions.append(Scan.part_type == part_type)
        if date_from is not None:
            conditions.append(Scan.created_at >= _naive_utc(date_from))
        if date_to is not None:
            conditions.append(Scan.created_at <= _naive_utc(date_to))
        if search:
            like = f"%{search}%"
            conditions.append(Scan.disease_name.ilike(like) | Scan.provider.ilike(like))
        if confidence_min is not None:
            conditions.append(Scan.confidence >= confidence_min)
        if confidence_max is not None:
            conditions.append(Scan.confidence <= confidence_max)
        if severity:
            conditions.append(Scan.severity == severity)
        if sync_status:
            conditions.append(Scan.sync_status == sync_status)

        where = and_(*conditions)
        total = await self.db.scalar(select(func.count()).select_from(Scan).where(where)) or 0

        sort_col = _SORT_COLUMNS.get(sort, Scan.created_at)
        order_expr = sort_col.desc() if order == "desc" else sort_col.asc()
        stmt = (
            select(Scan)
            .where(where)
            .order_by(order_expr)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        rows = (await self.db.scalars(stmt)).all()
        return list(rows), int(total)

    # ── Write ─────────────────────────────────────────────────────────

    async def create(self, payload: ScanCreate) -> Scan:
        """Persist one detection result and return the refreshed row."""
        scan = Scan(
            client_scan_id=payload.client_scan_id,
            user_id=payload.user_id,
            image_path=payload.image_path,
            media_items=payload.media_items,
            processed_image_path=payload.processed_image_path,
            crop_id=payload.crop_id,
            part_type=payload.part_type,
            disease_id=payload.disease_id,
            disease_name=payload.disease_name,
            confidence=payload.confidence,
            severity=payload.severity,
            stage=payload.stage,
            provider=payload.provider,
            model_name=payload.model_name,
            model_version=payload.model_version,
            dataset_version=payload.dataset_version,
            preprocessing_time_ms=payload.preprocessing_time_ms,
            inference_time_ms=payload.inference_time_ms,
            processing_time_ms=payload.processing_time_ms,
            ai_metadata=payload.ai_metadata,
            device_id=payload.device_id,
        )
        self.db.add(scan)
        await self.db.commit()
        await self.db.refresh(scan)
        logger.info(
            "scan_saved",
            scan_id=scan.id,
            user_id=payload.user_id,
            disease=payload.disease_name,
            confidence=payload.confidence,
        )
        return scan

    async def delete_for_user(self, scan_id: int, user_id: int, *, admin: bool = False) -> None:
        """Soft-delete a scan, audit-logging the actor (raises if no access).

        The row is marked ``deleted_at`` in the same transaction as the audit
        entry, so history/sync can never resurrect a deleted scan.
        """
        scan = await self.get_for_user(scan_id, user_id, admin=admin)
        scan.deleted_at = _now_naive_utc()
        self.db.add(scan)
        self.db.add(
            AuditLog(
                actor_id=user_id,
                action="scan.delete",
                resource_type="scan",
                resource_id=str(scan.id),
                details={
                    "client_scan_id": scan.client_scan_id,
                    "disease_name": scan.disease_name,
                },
            )
        )
        await self.db.commit()
        logger.info("scan_soft_deleted", scan_id=scan_id, actor_user_id=user_id)
