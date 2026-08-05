"""Knowledge-catalog schemas (read-only reference data for UI filters)."""

from pydantic import BaseModel, ConfigDict


class CropOut(BaseModel):
    """One catalog crop — the Scan History crop filter dropdown option."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    common_name: str | None
