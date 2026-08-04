"""Shared model primitives: timestamp mixin and role constants."""

from datetime import datetime

from sqlalchemy import DateTime, func
from sqlalchemy.orm import Mapped, mapped_column


class TimestampMixin:
    """Adds ``created_at`` / ``updated_at`` (DB-side UTC defaults)."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class UserRole:
    FARMER = "farmer"
    CUSTOMER = "customer"
    EXPERT = "expert"
    SELLER = "seller"
    ADMIN = "admin"

    ALL = (FARMER, CUSTOMER, EXPERT, SELLER, ADMIN)
