"""Current-user profile endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.user import UserOut, UserUpdate

router = APIRouter(prefix="/users", tags=["users"])

Db = Annotated[AsyncSession, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]


@router.get("/me", response_model=UserOut)
async def get_me(current_user: CurrentUser) -> User:
    return current_user


@router.patch("/me", response_model=UserOut)
async def update_me(payload: UserUpdate, db: Db, current_user: CurrentUser) -> User:
    for field, value in payload.model_dump(exclude_unset=True).items():
        if value is None and field == "name":  # name is non-nullable
            continue
        setattr(current_user, field, value)
    await db.commit()
    await db.refresh(current_user)
    return current_user
