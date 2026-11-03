
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.api.v1.deps import get_current_user
from app.models.user import User
from app.services.consultations import get_experts

router = APIRouter(prefix="/experts", tags=["Experts"])


@router.get("/")
async def list_experts(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    experts = await get_experts(db)

    return [
        {
            "user_id": profile.user_id,
            "name": account.name,
            "email": account.email,
            "avatar_url": account.avatar_url,
            "specialization": profile.specialization,
            "experience_years": profile.experience_years,
            "certifications": profile.certifications,
            "bio": profile.bio,
            "verified": profile.verified,
            "rating": profile.rating,
        }
        for profile, account in experts
    ]
