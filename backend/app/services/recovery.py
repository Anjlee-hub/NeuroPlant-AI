"""Crop recovery tracker service (M3, Task 4).

Aggregates a scan's ``RecoveryLog`` rows into a recovery timeline with a
computed percentage + status, and derives the dashboard's risk level. All of it
is *computed policy* — the heuristics below are documented constants, the
content is what the farmer records — so the Crop Doctor dashboard reads one
self-contained payload and never recomputes policy client-side.

``applied_at`` is stored naive-UTC for SQLite (the same convention the scan
service uses), so any client-supplied timestamp is normalized on write.

The **reminders seam**: a future M3/M4 reminder feature keys scheduled
follow-ups off the last log's ``applied_at`` and this scan id — nothing in the
schema or this service changes when that lands; it only reads the same timeline.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.catalog import Crop
from app.models.recovery import RecoveryLog
from app.models.scan import Scan
from app.schemas.recovery import (
    RecoveryLogIn,
    RecoveryLogOut,
    RecoveryLogUpdate,
    RecoveryScanOut,
    RecoveryTrackerOut,
)

logger = get_logger(__name__)

# ── Recovery policy ────────────────────────────────────────────────────────
# Computed, documented heuristics — the *content* is whatever the farmer logs.

# Starting recovery % right after diagnosis: lower-severity diseases are closer
# to recovered at detection, so they start further along.
RECOVERY_START_BY_SEVERITY: dict[str, float] = {
    "severe": 0.10,
    "moderate": 0.20,
    "low": 0.30,
}

# Each recorded treatment action advances recovery (treatment adherence step).
RECOVERY_STEP_PER_LOG: float = 0.15

# The latest farmer-reported crop response adjusts the trend.
RECOVERY_PROGRESS_ADJUST: dict[str, float] = {
    "worsening": -0.10,
    "no-change": 0.0,
    "improving": 0.10,
    "recovered": 0.20,
}

# Status bands on the 0–1 recovery percentage (inclusive lower bounds).
RECOVERY_STATUS_THRESHOLDS: tuple[tuple[str, float], ...] = (
    ("recovered", 0.95),
    ("improving", 0.60),
    ("on_track", 0.35),
    ("at_risk", 0.0),
)

# Risk level for the plant overview: severity band, escalated one notch when
# the detection confidence is low (the diagnosis itself is uncertain).
CONFIDENCE_LOW_THRESHOLD: float = 0.55
RISK_BY_SEVERITY: dict[str, str] = {"severe": "high", "moderate": "medium", "low": "low"}
_RISK_RANK: dict[str, int] = {"low": 0, "medium": 1, "high": 2}
_RISK_LABELS: tuple[str, str, str] = ("low", "medium", "high")


class RecoveryLogNotFoundError(Exception):
    """No recovery log with this id exists on this scan."""


def _now_naive_utc() -> datetime:
    """Current wall-clock as naive-UTC (SQLite stores naive UTC)."""
    return datetime.now(UTC).replace(tzinfo=None)


def _naive_utc(dt: datetime) -> datetime:
    """Normalize a client timestamp to naive-UTC."""
    if dt.tzinfo is None:
        return dt
    return dt.astimezone(UTC).replace(tzinfo=None)


class RecoveryTrackerService:
    """Reads/writes recovery logs and computes the tracker payload."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ── Read ───────────────────────────────────────────────────────────

    async def tracker(self, scan: Scan) -> RecoveryTrackerOut:
        """Self-contained recovery section for one scan.

        ``scan`` is expected to already be ownership-checked by the caller
        (same guard every scan endpoint uses).
        """
        logs = await self._logs_for_scan(scan.id)

        crop_name: str | None = None
        if scan.crop_id is not None:
            crop = await self.db.get(Crop, scan.crop_id)
            crop_name = crop.common_name if crop is not None else None

        pct = self.recovery_percentage(logs, scan.severity)
        updated = max((log.updated_at for log in logs), default=None)

        return RecoveryTrackerOut(
            scan=RecoveryScanOut(
                id=scan.id,
                disease_name=scan.disease_name,
                crop_id=scan.crop_id,
                crop_name=crop_name,
                part_type=scan.part_type,
                severity=scan.severity,
                stage=scan.stage,
                confidence=scan.confidence,
                provider=scan.provider,
                model_version=scan.model_version,
                created_at=scan.created_at,
            ),
            risk=self.risk(scan),
            recovery_percentage=pct,
            status=self.status(pct),
            total_treatments=len(logs),
            timeline=[RecoveryLogOut.model_validate(log) for log in logs],
            updated_at=updated,
        )

    # ── Write ──────────────────────────────────────────────────────────

    async def add_log(self, scan: Scan, payload: RecoveryLogIn) -> RecoveryLogOut:
        """Record one treatment action against the scan."""
        log = RecoveryLog(
            scan_id=scan.id,
            user_id=scan.user_id,
            treatment_applied=payload.treatment_applied,
            notes=payload.notes,
            progress=payload.progress,
            applied_at=(
                _naive_utc(payload.applied_at) if payload.applied_at else _now_naive_utc()
            ),
        )
        self.db.add(log)
        await self.db.commit()
        await self.db.refresh(log)
        logger.info("recovery_log_added", scan_id=scan.id, log_id=log.id)
        return RecoveryLogOut.model_validate(log)

    async def update_log(
        self, scan: Scan, log_id: int, payload: RecoveryLogUpdate
    ) -> RecoveryLogOut:
        """Apply a partial edit to one of the scan's logs."""
        log = await self._log_for_scan(scan.id, log_id)
        for field, value in payload.model_dump(exclude_unset=True).items():
            if field == "applied_at":
                if value is not None:
                    log.applied_at = _naive_utc(value)
                continue
            setattr(log, field, value)
        self.db.add(log)
        await self.db.commit()
        await self.db.refresh(log)
        logger.info("recovery_log_updated", scan_id=scan.id, log_id=log.id)
        return RecoveryLogOut.model_validate(log)

    async def delete_log(self, scan: Scan, log_id: int) -> None:
        """Remove one of the scan's logs."""
        log = await self._log_for_scan(scan.id, log_id)
        await self.db.delete(log)
        await self.db.commit()
        logger.info("recovery_log_deleted", scan_id=scan.id, log_id=log.id)

    # ── Internals ──────────────────────────────────────────────────────

    async def _logs_for_scan(self, scan_id: int) -> list[RecoveryLog]:
        """Chronological timeline (applied order, ties by insertion)."""
        rows = await self.db.scalars(
            select(RecoveryLog)
            .where(RecoveryLog.scan_id == scan_id)
            .order_by(RecoveryLog.applied_at.asc(), RecoveryLog.id.asc())
        )
        return list(rows.all())

    async def _log_for_scan(self, scan_id: int, log_id: int) -> RecoveryLog:
        """One log owned by this scan (raises when absent)."""
        log = await self.db.scalar(
            select(RecoveryLog).where(
                RecoveryLog.id == log_id,
                RecoveryLog.scan_id == scan_id,
            )
        )
        if log is None:
            raise RecoveryLogNotFoundError(f"recovery log {log_id} not found for scan {scan_id}")
        return log

    # ── Policy ─────────────────────────────────────────────────────────

    @staticmethod
    def recovery_percentage(logs: list[RecoveryLog], severity: str | None) -> float:
        """0–1 estimate: severity start + one step per logged treatment +
        the latest reported trend. Clamped to [0, 1]."""
        base = RECOVERY_START_BY_SEVERITY.get(severity or "", 0.20)
        steps = len(logs) * RECOVERY_STEP_PER_LOG
        latest = logs[-1].progress if logs else None
        adjust = RECOVERY_PROGRESS_ADJUST.get(latest or "", 0.0)
        return round(max(0.0, min(1.0, base + steps + adjust)), 2)

    @staticmethod
    def status(percentage: float) -> str:
        """Map a 0–1 percentage to a recovery band."""
        for label, threshold in RECOVERY_STATUS_THRESHOLDS:
            if percentage >= threshold:
                return label
        return "at_risk"

    @staticmethod
    def risk(scan: Scan) -> str:
        """Risk band from severity, escalated when detection confidence is low."""
        base = RISK_BY_SEVERITY.get(scan.severity or "", "medium")
        low_confidence = scan.confidence < CONFIDENCE_LOW_THRESHOLD
        if low_confidence and _RISK_RANK[base] < _RISK_RANK["high"]:
            return _RISK_LABELS[_RISK_RANK[base] + 1]
        return base
