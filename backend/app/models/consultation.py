
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base
from app.models.base import TimestampMixin


class Consultation(Base, TimestampMixin):
    __tablename__ = "consultations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    farmer_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
    )

    expert_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
    )

    subject: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text)

    status: Mapped[str] = mapped_column(
        String(30), default="pending", index=True
    )

    scheduled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    expert_response: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
