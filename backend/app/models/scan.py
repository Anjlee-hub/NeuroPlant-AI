"""Scan records — AI disease-detection results and their provenance.

One row per detection run. Design notes:

- ``media_items`` is the source-agnostic image seam (upload | camera | drone |
  satellite | iot) so the Crop Doctor and future ingestion adapters reuse the
  same shape; M2 stores a single upload item.
- ``client_scan_id`` is the offline idempotency key (client-generated UUID) —
  the sync endpoint re-sends it and the server returns the existing row.
- ``sync_status`` / ``sync_error`` / ``synced_at`` prepare the offline queue
  (Task 6) without implementing it yet.
- ``processed_image_path`` / ``heatmap_path`` are the explainability hooks for
  Grad-CAM (Task 5): the padded model-input image and the generated heatmap.
"""

from datetime import datetime

from sqlalchemy import (
    JSON,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base
from app.models.base import TimestampMixin


class Scan(Base, TimestampMixin):
    __tablename__ = "scans"
    __table_args__ = (
        Index("ix_scans_user_created", "user_id", "created_at"),
        # Covers the common history query: own rows, not soft-deleted, by recency.
        Index("ix_scans_user_deleted_created", "user_id", "deleted_at", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    # Offline idempotency key — client-generated, globally unique.
    client_scan_id: Mapped[str] = mapped_column(String(36), unique=True, index=True, nullable=False)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )

    # Source image(s) — MediaItem seam (list of dicts).
    media_items: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    image_path: Mapped[str] = mapped_column(String(500), nullable=False)  # sanitized
    processed_image_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    heatmap_path: Mapped[str | None] = mapped_column(String(500), nullable=True)  # Task 5

    # Classification context.
    crop_id: Mapped[int | None] = mapped_column(
        ForeignKey("crops.id", ondelete="SET NULL"), nullable=True, index=True
    )
    part_type: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # Prediction.
    disease_id: Mapped[int | None] = mapped_column(
        ForeignKey("diseases.id", ondelete="SET NULL"), nullable=True, index=True
    )
    disease_name: Mapped[str] = mapped_column(String(160), index=True, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    severity: Mapped[str | None] = mapped_column(String(20), nullable=True)
    stage: Mapped[str | None] = mapped_column(String(60), nullable=True)

    # Provenance & timing.
    provider: Mapped[str] = mapped_column(String(40), default="baseline", nullable=False)
    model_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    model_version: Mapped[str | None] = mapped_column(String(60), nullable=True)
    dataset_version: Mapped[str | None] = mapped_column(String(40), nullable=True)
    preprocessing_time_ms: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    inference_time_ms: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    processing_time_ms: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    # AI metadata (rankings, symptoms, model config — full explainability hooks).
    ai_metadata: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Offline sync / idempotency (prepared, not yet used — Task 6).
    sync_status: Mapped[str] = mapped_column(String(20), default="synced", nullable=False)
    sync_error: Mapped[str | None] = mapped_column(String(500), nullable=True)
    device_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Soft delete (Task 4.3): NULL = live, set = deleted. History/detail/sync
    # queries filter on it so a deleted scan never resurfaces.
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    @property
    def rankings(self) -> list[dict]:
        """Top-k candidates from ``ai_metadata`` (or empty)."""
        if not self.ai_metadata:
            return []
        return self.ai_metadata.get("rankings", [])
