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

from app.core.logging import get_logger
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


class ScanService:
    """All Scan persistence/querying behind one dependency-injectable class."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ── Read ──────────────────────────────────────────────────────────

    async def get_for_user(self, scan_id: int, user_id: int) -> Scan:
        """Ownership-guarded detail lookup."""
        row = await self.db.get(Scan, scan_id)
        if row is None or row.user_id != user_id:
            raise ScanNotFoundError(f"scan {scan_id} not found for user {user_id}")
        return row

    async def find_by_client_id(self, client_scan_id: str, user_id: int) -> Scan | None:
        """Idempotency lookup used by the offline-sync path (Task 6)."""
        return await self.db.scalar(
            select(Scan).where(
                Scan.client_scan_id == client_scan_id,
                Scan.user_id == user_id,
            )
        )

    async def list_scans(
        self,
        user_id: int,
        *,
        crop_id: int | None = None,
        disease: str | None = None,
        part_type: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        search: str | None = None,
        sort: str = "created_at",
        order: str = "desc",
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Scan], int]:
        """Paginated, filtered history. Returns ``(rows, total_count)``."""
        conditions = [Scan.user_id == user_id]
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

    async def delete_for_user(self, scan_id: int, user_id: int) -> None:
        """Ownership-guarded delete (raises :class:`ScanNotFoundError`)."""
        scan = await self.get_for_user(scan_id, user_id)
        await self.db.delete(scan)
        await self.db.commit()
        logger.info("scan_deleted", scan_id=scan_id, user_id=user_id)
