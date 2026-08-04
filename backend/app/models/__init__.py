"""SQLAlchemy ORM models.

Import every model module here so ``Base.metadata`` is fully populated for
Alembic autogenerate and test ``create_all``.
"""

from app.models.catalog import Crop, Disease
from app.models.user import (
    MFA,
    Device,
    ExpertProfile,
    FarmerProfile,
    LoginEvent,
    OtpCode,
    RefreshToken,
    SellerProfile,
    User,
)

__all__ = [
    "Crop",
    "Disease",
    "User",
    "FarmerProfile",
    "ExpertProfile",
    "SellerProfile",
    "MFA",
    "Device",
    "LoginEvent",
    "RefreshToken",
    "OtpCode",
]
