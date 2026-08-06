"""Crop recovery tracker schemas (M3, Task 4).

The tracker is the Crop Doctor dashboard's recovery section: a farmer logs
treatment actions (``RecoveryLogIn``) against a scan and the engine aggregates
them into a recovery timeline with a computed percentage + status
(:class:`RecoveryTrackerOut`). The same payload carries a compact scan summary
so the dashboard's Plant Overview renders from one call.

The recovery percentage / status / risk are *computed policy* (documented in
``app.services.recovery``), never stored — so the constants in the service are
the single source of truth and every band agrees with the schemas' vocabularies.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

# Farmer-reported crop response for one treatment log.
RECOVERY_PROGRESS = ("worsening", "no-change", "improving", "recovered")

# Computed recovery bands (ascending).
RECOVERY_STATUS = ("at_risk", "on_track", "improving", "recovered")

# Computed risk levels for the plant overview.
RISK_LEVELS = ("low", "medium", "high")


class RecoveryLogIn(BaseModel):
    """POST /scans/{id}/recovery/logs — record one treatment action."""

    treatment_applied: str = Field(
        min_length=1,
        max_length=500,
        description="What the farmer applied / did (e.g. 'Neem oil spray')",
    )
    notes: str | None = Field(
        default=None, max_length=2000, description="Free-form progress notes"
    )
    progress: str | None = Field(
        default=None,
        pattern="^(worsening|no-change|improving|recovered)$",
        description="Farmer-reported crop response (optional)",
    )
    applied_at: datetime | None = Field(
        default=None, description="When the treatment was applied (defaults to now)"
    )


class RecoveryLogUpdate(BaseModel):
    """PATCH /scans/{id}/recovery/logs/{log_id} — partial edit of one log.

    Only the fields the client actually sends are applied (``exclude_unset``),
    so omitting ``notes`` keeps the old value while sending ``notes: null``
    clears it.
    """

    treatment_applied: str | None = Field(
        default=None, min_length=1, max_length=500
    )
    notes: str | None = Field(default=None, max_length=2000)
    progress: str | None = Field(
        default=None, pattern="^(worsening|no-change|improving|recovered)$"
    )
    applied_at: datetime | None = Field(default=None)


class RecoveryLogOut(BaseModel):
    """One treatment log as returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    scan_id: int
    treatment_applied: str
    notes: str | None
    progress: str | None
    applied_at: datetime
    created_at: datetime


class RecoveryScanOut(BaseModel):
    """Compact scan summary that drives the dashboard's Plant Overview.

    Includes the resolved ``crop_name`` so the dashboard needs no extra catalog
    call to label the crop.
    """

    id: int
    disease_name: str
    crop_id: int | None
    crop_name: str | None
    part_type: str | None
    severity: str | None
    stage: str | None
    confidence: float
    provider: str
    model_version: str | None
    created_at: datetime


class RecoveryTrackerOut(BaseModel):
    """GET /scans/{id}/recovery — the whole recovery section in one payload.

    ``risk`` is computed from the scan's severity + detection confidence,
    ``recovery_percentage``/``status`` from severity + the logged treatments,
    and ``timeline`` is the applied-ordered list of treatment logs. Lists are
    always present (never null) so the frontend can map over them safely.
    """

    scan: RecoveryScanOut
    risk: str = Field(description="low | medium | high (computed)")
    recovery_percentage: float = Field(
        ge=0.0, le=1.0, description="Estimated recovery progress (0–1)"
    )
    status: str = Field(description="at_risk | on_track | improving | recovered")
    total_treatments: int = Field(description="Logged treatment actions")
    timeline: list[RecoveryLogOut] = Field(default_factory=list)
    updated_at: datetime | None = Field(
        default=None, description="Last log update; null when no logs yet"
    )
