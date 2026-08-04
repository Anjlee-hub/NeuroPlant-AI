"""Audit trail — append-only log of sensitive / destructive actions.

M10 builds the full admin console around this table; today it records
destructive actions (scan deletion) with actor + resource identity so there is
always a paper trail. Rows are never updated or deleted by application code.
"""

from sqlalchemy import JSON, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base
from app.models.base import TimestampMixin


class AuditLog(Base, TimestampMixin):
    __tablename__ = "audit_logs"
    __table_args__ = (
        Index("ix_audit_logs_actor_created", "actor_id", "created_at"),
        Index("ix_audit_logs_resource", "resource_type", "resource_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    actor_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    action: Mapped[str] = mapped_column(String(64), nullable=False)  # e.g. scan.delete
    resource_type: Mapped[str] = mapped_column(String(32), nullable=False)  # scan
    resource_id: Mapped[str] = mapped_column(String(64), nullable=False)
    details: Mapped[dict | None] = mapped_column(JSON, nullable=True)
