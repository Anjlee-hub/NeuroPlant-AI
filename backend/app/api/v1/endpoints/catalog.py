"""Read-only knowledge-catalog endpoints (UI filter options).

``GET /catalog/crops`` powers the Scan History crop-filter dropdown (Task 7.1).
The catalog is reference data; nothing here mutates it.
"""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_current_user
from app.db.session import get_db
from app.models.catalog import Crop
from app.models.user import User
from app.schemas.catalog import CropOut

router = APIRouter(prefix="/catalog", tags=["catalog"])

Db = Annotated[AsyncSession, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]


@router.get("/crops", response_model=list[CropOut])
async def list_crops(_current_user: CurrentUser, db: Db) -> list[Crop]:
    """All catalog crops, ordered by name."""
    rows = (await db.execute(select(Crop).order_by(Crop.name))).scalars().all()
    return list(rows)
