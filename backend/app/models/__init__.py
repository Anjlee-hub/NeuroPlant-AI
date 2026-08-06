"""SQLAlchemy ORM models.

Import every model module here so ``Base.metadata`` is fully populated for
Alembic autogenerate and test ``create_all``.
"""

from app.models.audit import AuditLog
from app.models.calendar import (
    CalendarTask,
    CropCalendarCatalog,
    CropCalendarPlan,
    CropSchedule,
)
from app.models.catalog import Crop, Disease
from app.models.recommendation import DiseaseRecommendation, RecommendationCatalog
from app.models.recovery import RecoveryLog
from app.models.scan import Scan
from app.models.soil import SoilRecommendation, SoilRecommendationCatalog
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
    "AuditLog",
    "CalendarTask",
    "CropCalendarCatalog",
    "CropCalendarPlan",
    "CropSchedule",
    "Crop",
    "Disease",
    "RecommendationCatalog",
    "DiseaseRecommendation",
    "SoilRecommendationCatalog",
    "SoilRecommendation",
    "RecoveryLog",
    "Scan",
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
