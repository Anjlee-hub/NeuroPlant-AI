"""Scan API schemas — request/response DTOs for the detection pipeline.

``POST /scans`` is multipart (image files + form fields), so the create request
is modelled as the service-level :class:`ScanCreate`; the response layer uses
:class:`ScanOut` (``from_attributes`` so ORM rows serialize directly).
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

# Plant part the scan focuses on (leaf | fruit | stem | plant | whole).
PART_TYPES = ("leaf", "fruit", "stem", "plant", "whole")

# Client-generated offline idempotency key: 8-4-4-4-12 UUID string.
CLIENT_SCAN_ID_PATTERN = (
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)


class ScanCreate(BaseModel):
    """Everything the service persists for one detection run."""

    client_scan_id: str = Field(pattern=CLIENT_SCAN_ID_PATTERN)
    user_id: int
    image_path: str
    media_items: list = Field(default_factory=list)
    processed_image_path: str | None = None

    crop_id: int | None = None
    part_type: str | None = Field(default=None, pattern="^(leaf|fruit|stem|plant|whole)$")

    disease_id: int | None = None
    disease_name: str = Field(min_length=1)
    confidence: float = Field(ge=0.0, le=1.0)
    severity: str | None = None
    stage: str | None = None

    provider: str = Field(min_length=1)
    model_name: str | None = None
    model_version: str | None = None
    dataset_version: str | None = None
    preprocessing_time_ms: float = Field(default=0.0, ge=0.0)
    inference_time_ms: float = Field(default=0.0, ge=0.0)
    processing_time_ms: float = Field(default=0.0, ge=0.0)
    ai_metadata: dict | None = None
    device_id: str | None = None


class RankingOut(BaseModel):
    """One ranked alternative candidate (top-k)."""

    disease_name: str
    confidence: float = Field(ge=0.0, le=1.0)
    disease_id: int | None = None
    crop_id: int | None = None


class ScanOut(BaseModel):
    """A persisted scan as returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    client_scan_id: str
    crop_id: int | None
    part_type: str | None
    disease_id: int | None
    disease_name: str
    confidence: float
    severity: str | None
    stage: str | None
    provider: str
    model_name: str | None
    model_version: str | None
    dataset_version: str | None
    preprocessing_time_ms: float
    inference_time_ms: float
    processing_time_ms: float
    image_path: str
    media_items: list
    sync_status: str
    rankings: list[RankingOut] = Field(default_factory=list)
    created_at: datetime


class ScanListOut(BaseModel):
    """Paginated scan history."""

    items: list[ScanOut]
    total: int
    page: int
    page_size: int
    has_next: bool
