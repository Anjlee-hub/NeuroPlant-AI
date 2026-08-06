"""Crop recovery tracker (M3, Task 4).

One row per treatment action a farmer records against a diagnosed scan — what
was applied, when, and how the crop is responding. Rows are owned by a scan
(and, denormalized, its user) so the tracker endpoints reuse the scan ownership
guard and the Crop Doctor dashboard renders the whole recovery timeline from a
single payload.

``progress`` is the farmer-reported crop response (``worsening | no-change |
improving | recovered``) — the trend signal the recovery status is computed
from. It is optional because a farmer may log a treatment without classifying
the outcome; the service then leans purely on severity + treatment count.
"""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base
from app.models.base import TimestampMixin


class RecoveryLog(Base, TimestampMixin):
    __tablename__ = "recovery_logs"
    __table_args__ = (
        # The tracker always renders the timeline in applied order per scan.
        Index("ix_recovery_logs_scan_applied", "scan_id", "applied_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    scan_id: Mapped[int] = mapped_column(
        ForeignKey("scans.id", ondelete="CASCADE"), index=True, nullable=False
    )
    # Denormalized for direct, index-friendly ownership filtering.
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )

    # What the farmer applied / did (required, free-form).
    treatment_applied: Mapped[str] = mapped_column(String(500), nullable=False)

    # Free-form progress notes (optional).
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Reported crop response — the trend signal for the recovery status.
    # worsening | no-change | improving | recovered
    progress: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # When the treatment was applied (defaults to now server-side).
    applied_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
