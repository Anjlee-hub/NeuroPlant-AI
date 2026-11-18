"""Represent unavailable baseline confidence as NULL.

Revision ID: a8c4e2f6b0d1
Revises: f6a2c8e0b1d3
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "a8c4e2f6b0d1"
down_revision: str | None = "f6a2c8e0b1d3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("scans") as batch_op:
        batch_op.alter_column(
            "confidence",
            existing_type=sa.Float(),
            nullable=True,
        )

    scans = sa.table(
        "scans",
        sa.column("id", sa.Integer),
        sa.column("provider", sa.String),
        sa.column("confidence", sa.Float),
        sa.column("ai_metadata", sa.JSON),
    )
    connection = op.get_bind()
    rows = connection.execute(
        sa.select(scans.c.id, scans.c.ai_metadata).where(scans.c.provider == "baseline")
    )
    for row in rows:
        metadata = dict(row.ai_metadata or {})
        metadata["confidence"] = {"top": None, "level": "unavailable"}
        for key in ("top5", "rankings"):
            candidates = metadata.get(key)
            if isinstance(candidates, list):
                metadata[key] = [
                    {**candidate, "confidence": None}
                    if isinstance(candidate, dict)
                    else candidate
                    for candidate in candidates
                ]
        connection.execute(
            scans.update()
            .where(scans.c.id == row.id)
            .values(confidence=None, ai_metadata=metadata)
        )


def downgrade() -> None:
    scans = sa.table("scans", sa.column("confidence", sa.Float))
    connection = op.get_bind()
    if connection.execute(
        sa.select(sa.func.count()).select_from(scans).where(scans.c.confidence.is_(None))
    ).scalar_one():
        raise RuntimeError(
            "Cannot require scan confidence while scans have unavailable model confidence."
        )

    with op.batch_alter_table("scans") as batch_op:
        batch_op.alter_column(
            "confidence",
            existing_type=sa.Float(),
            nullable=False,
        )
