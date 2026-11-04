from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.consultation import (
    ConsultationCreate,
    ConsultationResponse,
    ConsultationUpdate,
)
from app.services import consultations

router = APIRouter(prefix="/consultations", tags=["Consultations"])


@router.post("/", response_model=ConsultationResponse)
async def request_consultation(
    data: ConsultationCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if user.role != "farmer":
        raise HTTPException(403, "Only farmers can request consultations")

    result = await consultations.create_consultation(db, user.id, data)
    if result is None:
        raise HTTPException(404, "Expert not found")
    return result


@router.get("/", response_model=list[ConsultationResponse])
async def list_consultations(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return await consultations.get_user_consultations(db, user.id)


@router.patch("/{consultation_id}", response_model=ConsultationResponse)
async def update_consultation(
    consultation_id: int,
    data: ConsultationUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if user.role != "expert":
        raise HTTPException(403, "Only experts can update consultations")

    result = await consultations.update_consultation(db, consultation_id, user.id, data)
    if result is None:
        raise HTTPException(404, "Consultation not found or invalid update")
    return result
