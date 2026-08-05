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
    heatmap_path: str | None = None  # Grad-CAM overlay (Task 5.2)

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

    disease_name: str = Field(description="Alternative disease name")
    confidence: float = Field(ge=0.0, le=1.0, description="Model confidence in [0, 1]")
    disease_id: int | None = Field(default=None, description="Catalog disease id")
    crop_id: int | None = Field(default=None, description="Catalog crop id")


class ExplainDiseaseOut(BaseModel):
    """The predicted disease plus catalog detail for the explain payload."""

    id: int | None = Field(default=None, description="Catalog disease id")
    name: str = Field(description="Predicted disease name")
    crop_id: int | None = Field(default=None, description="Catalog crop id")
    severity: str | None = Field(default=None, description="low | moderate | severe")
    stage: str | None = Field(default=None, description="Growth stage, e.g. early")
    symptoms: list[str] = Field(default_factory=list, description="Catalog symptoms to look for")


class ExplainConfidenceOut(BaseModel):
    """Top confidence, its band, and expert advice (Task 5.3 low-confidence path)."""

    top: float = Field(ge=0.0, le=1.0, description="Top-1 model confidence in [0, 1]")
    level: str = Field(description="Confidence band: high | medium | low")
    advice: str = Field(description="Plain-language expert advice for this band")


class ExplainHeatmapOut(BaseModel):
    """How / when the Grad-CAM heatmap was produced (Task 5.2 provenance)."""

    provider: str = Field(description="Grad-CAM implementation, e.g. baseline")
    class_name: str = Field(description="Class the heatmap was computed for")
    time_ms: float = Field(ge=0.0, description="Grad-CAM generation time (ms)")


class ExplainModelOut(BaseModel):
    """Serving model provenance for the stored prediction."""

    provider: str = Field(description="Serving provider, e.g. baseline | tensorflow")
    model_name: str | None = Field(default=None, description="Model architecture name")
    model_version: str | None = Field(default=None, description="Model artifact version")
    dataset_version: str | None = Field(default=None, description="Training dataset version")


class ExplainTimingOut(BaseModel):
    """Measured latency for the detection + explainability stages (Task 5.4).

    All values are milliseconds, captured at prediction time and stored on the
    scan row; ``heatmap_time_ms`` is ``None`` when no heatmap was generated.
    """

    preprocessing_time_ms: float = Field(ge=0.0, description="Image validation + padding (ms)")
    inference_time_ms: float = Field(ge=0.0, description="Classifier inference (ms)")
    processing_time_ms: float = Field(ge=0.0, description="End-to-end upload→persist (ms)")
    heatmap_time_ms: float | None = Field(
        default=None, ge=0.0, description="Grad-CAM generation (ms); None when absent"
    )


class ScanExplainOut(BaseModel):
    """GET /scans/{id}/explain — the explainability payload.

    Heatmap + overlay (as storage URLs), a plain-language explanation, the full
    ranked top-5 with per-candidate confidence, the metadata behind the
    diagnosis (confidence band + expert advice, Grad-CAM + model provenance,
    pipeline timing), and a graceful degrade when no heatmap exists.
    """

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "scan_id": 42,
                    "disease": {
                        "id": 15,
                        "name": "Late Blight",
                        "crop_id": 101,
                        "severity": "moderate",
                        "stage": "early",
                        "symptoms": [
                            "Dark water-soaked lesions",
                            "White fungal ring in high humidity",
                        ],
                    },
                    "confidence": {
                        "top": 0.92,
                        "level": "high",
                        "advice": (
                            "High-confidence result — the pattern is a strong match for this "
                            "disease. Treat accordingly, but confirm the symptoms first."
                        ),
                    },
                    "top5": [
                        {
                            "disease_name": "Late Blight",
                            "confidence": 0.92,
                            "disease_id": 15,
                            "crop_id": 101,
                        },
                        {
                            "disease_name": "Early Blight",
                            "confidence": 0.04,
                            "disease_id": 1,
                            "crop_id": 101,
                        },
                    ],
                    "heatmap": {
                        "provider": "baseline",
                        "class_name": "Late Blight",
                        "time_ms": 18.2,
                    },
                    "heatmap_url": "/media/42/heatmaps/ab12cd34ef56.png",
                    "overlay_url": "/media/42/heatmaps/ab12cd34ef78.png",
                    "explanation": "This photo was classified as Late Blight with 92% confidence. "
                    "The heatmap overlay marks the image regions the model focused on. "
                    "The pattern is consistent with moderate severity at the early stage.",
                    "timing": {
                        "preprocessing_time_ms": 12.4,
                        "inference_time_ms": 8.1,
                        "processing_time_ms": 31.9,
                        "heatmap_time_ms": 18.2,
                    },
                    "model": {
                        "provider": "baseline",
                        "model_name": "rule-baseline",
                        "model_version": "baseline-v1",
                        "dataset_version": "v1",
                    },
                }
            ]
        },
    )

    scan_id: int = Field(description="The scan row id")
    disease: ExplainDiseaseOut
    confidence: ExplainConfidenceOut
    top5: list[RankingOut] = Field(default_factory=list, description="Ordered top-5 candidates")
    heatmap: ExplainHeatmapOut | None = Field(
        default=None, description="Grad-CAM provenance; None when no heatmap exists"
    )
    heatmap_url: str | None = Field(default=None, description="Storage URL of the raw heatmap PNG")
    overlay_url: str | None = Field(default=None, description="Storage URL of the Jet overlay PNG")
    explanation: str = Field(description="Plain-language 'why' behind the diagnosis")
    timing: ExplainTimingOut
    model: ExplainModelOut


class ScanOut(BaseModel):
    """A persisted scan as returned by the API (complete detail record)."""

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "examples": [
                {
                    "id": 42,
                    "client_scan_id": "e8d4f9a2-3c1b-4e6a-9d5f-2b7a8c0d1e3f",
                    "crop_id": 101,
                    "part_type": "leaf",
                    "disease_id": 15,
                    "disease_name": "Late Blight",
                    "confidence": 0.92,
                    "severity": "moderate",
                    "stage": "early",
                    "provider": "baseline",
                    "model_name": "rule-baseline",
                    "model_version": "baseline-v1",
                    "dataset_version": "v1",
                    "preprocessing_time_ms": 12.4,
                    "inference_time_ms": 8.1,
                    "processing_time_ms": 31.9,
                    "image_path": "42/scans/ab12cd34ef56.jpg",
                    "processed_image_path": "42/processed/ab12cd34ef56.jpg",
                    "heatmap_path": "42/heatmaps/ab12cd34ef56.png",
                    "media_items": [
                        {
                            "source_type": "upload",
                            "path": "42/scans/ab12cd34ef56.jpg",
                            "url": "/media/42/scans/ab12cd34ef56.jpg",
                            "part_type": "leaf",
                            "width": 224,
                            "height": 224,
                            "content_type": "image/jpeg",
                        }
                    ],
                    "sync_status": "synced",
                    "rankings": [
                        {"disease_name": "Late Blight", "confidence": 0.92, "disease_id": 15}
                    ],
                    "created_at": "2026-08-04T09:14:52",
                }
            ]
        },
    )

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
    processed_image_path: str | None = None  # padded model-input image (Task 5)
    heatmap_path: str | None = None  # Grad-CAM overlay (Task 5.2)
    media_items: list
    sync_status: str
    rankings: list[RankingOut] = Field(default_factory=list)
    # Full explainability payload (top-k candidates, symptoms, model config).
    ai_metadata: dict | None = None
    created_at: datetime


class ScanListOut(BaseModel):
    """Paginated scan history."""

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "examples": [
                {
                    "items": [
                        {
                            "id": 42,
                            "disease_name": "Late Blight",
                            "confidence": 0.92,
                            "severity": "moderate",
                            "provider": "baseline",
                            "created_at": "2026-08-04T09:14:52",
                        }
                    ],
                    "total": 1,
                    "page": 1,
                    "page_size": 20,
                    "has_next": False,
                }
            ]
        },
    )

    items: list[ScanOut]
    total: int
    page: int
    page_size: int
    has_next: bool
