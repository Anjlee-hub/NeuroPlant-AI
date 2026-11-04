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
from app.models.community import (
    CommunityComment,
    CommunityPost,
    CommunityVote,
)
from app.models.consultation import Consultation
from app.models.conversation import ConversationMessage
from app.models.marketplace import CropListing, Product
from app.models.marketplace_trust import MarketplaceFavorite, MarketplaceReview
from app.models.messaging import MarketplaceConversation, MarketplaceMessage
from app.models.notification import Notification, NotificationType
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
    "CommunityComment",
    "CommunityPost",
    "CommunityVote",
    "Consultation",
    "ConversationMessage",
    "CropListing",
    "Product",
    "MarketplaceFavorite",
    "MarketplaceReview",
    "MarketplaceConversation",
    "MarketplaceMessage",
    "Notification",
    "NotificationType",
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
