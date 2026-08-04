"""User / profile schemas."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    role: str
    phone: str
    email: str | None
    name: str
    avatar_url: str | None
    lang: str
    verified: bool
    created_at: datetime


class UserUpdate(BaseModel):
    name: str | None = None
    lang: str | None = None
    address: str | None = None
    lat: float | None = None
    lng: float | None = None
