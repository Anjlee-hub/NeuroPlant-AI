
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class ConsultationCreate(BaseModel):
    expert_id: int
    subject: str = Field(min_length=3, max_length=200)
    description: str = Field(min_length=1)
    scheduled_at: datetime | None = None


class ConsultationUpdate(BaseModel):
    status: str | None = None
    expert_response: str | None = None


class ConsultationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    farmer_id: int
    expert_id: int
    subject: str
    description: str
    status: str
    scheduled_at: datetime | None
    expert_response: str | None
