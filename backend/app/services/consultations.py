
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.consultation import Consultation
from app.models.user import User, ExpertProfile


async def create_consultation(db: AsyncSession, farmer_id: int, data):
    expert = await db.get(User, data.expert_id)

    if not expert or expert.role != "expert":
        return None

    consultation = Consultation(
        farmer_id=farmer_id,
        **data.model_dump(),
    )
    db.add(consultation)
    await db.commit()
    await db.refresh(consultation)
    return consultation


async def get_user_consultations(db: AsyncSession, user_id: int):
    result = await db.execute(
        select(Consultation).where(
            or_(
                Consultation.farmer_id == user_id,
                Consultation.expert_id == user_id,
            )
        ).order_by(Consultation.id.desc())
    )
    return result.scalars().all()


async def update_consultation(db: AsyncSession, consultation_id: int, expert_id: int, data):
    consultation = await db.get(Consultation, consultation_id)

    if not consultation or consultation.expert_id != expert_id:
        return None

    updates = data.model_dump(exclude_unset=True)

    if updates.get("status") not in (
        None, "pending", "accepted", "rejected", "completed"
    ):
        return None

    for key, value in updates.items():
        setattr(consultation, key, value)

    await db.commit()
    await db.refresh(consultation)
    return consultation


async def get_experts(db: AsyncSession):
    result = await db.execute(
        select(ExpertProfile, User)
        .join(User, ExpertProfile.user_id == User.id)
        .where(User.status == "active")
    )
    return result.all()
