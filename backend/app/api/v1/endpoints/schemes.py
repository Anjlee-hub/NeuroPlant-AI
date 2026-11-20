"""Grounded government scheme discovery and eligibility checks."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_current_user, require_roles
from app.db.session import get_db
from app.models.scheme import GovernmentScheme
from app.models.user import User
from app.schemas.scheme import (
    EligibilityCheckIn,
    EligibilityCheckOut,
    GovernmentSchemeCreate,
    GovernmentSchemeOut,
    GovernmentSchemePageOut,
)
from app.services.schemes import SCHEME_SOURCE_UNAVAILABLE, GovernmentSchemeService

router = APIRouter(prefix="/schemes", tags=["government schemes"])

Db = Annotated[AsyncSession, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]
AdminUser = Annotated[User, Depends(require_roles("admin"))]


def _scheme_out(scheme: GovernmentScheme) -> GovernmentSchemeOut:
    output = GovernmentSchemeOut.model_validate(scheme)
    if not scheme.is_verified:
        output.official_application_url = None
        output.subsidy_details = None
    return output


@router.get("", response_model=GovernmentSchemePageOut)
async def list_schemes(
    user: CurrentUser,
    db: Db,
    state_code: Annotated[str | None, Query(min_length=2, max_length=8)] = None,
    crop_name: Annotated[str | None, Query(min_length=1, max_length=120)] = None,
    farmer_category: Annotated[str | None, Query(min_length=1, max_length=80)] = None,
    category: Annotated[str | None, Query(min_length=2, max_length=80)] = None,
    district_code: Annotated[str | None, Query(min_length=1, max_length=120)] = None,
    search: Annotated[str | None, Query(min_length=1, max_length=200)] = None,
    status: Annotated[str | None, Query(pattern="^(active|closed|unverified)$")] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> GovernmentSchemePageOut:
    items, total = await GovernmentSchemeService(db).list(
        user.id,
        state_code=state_code,
        crop_name=crop_name,
        farmer_category=farmer_category,
        category=category,
        district_code=district_code,
        search=search,
        status=status,
        page=page,
        page_size=page_size,
    )
    return GovernmentSchemePageOut(
        items=[_scheme_out(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
        pages=(total + page_size - 1) // page_size if total else 0,
        source_status="scheme_records_available" if total else "no_scheme_records",
        source_note=(
            "Records are curated from attributed sources; check each record's verification status."
            if total
            else SCHEME_SOURCE_UNAVAILABLE
        ),
    )


@router.get("/saved", response_model=list[GovernmentSchemeOut])
async def list_saved_schemes(
    user: CurrentUser,
    db: Db,
) -> list[GovernmentSchemeOut]:
    schemes = await GovernmentSchemeService(db).list_saved(user.id)
    return [_scheme_out(scheme) for scheme in schemes]


@router.get("/saved/status/{scheme_id}", response_model=dict[str, bool])
async def saved_status(
    scheme_id: int,
    user: CurrentUser,
    db: Db,
) -> dict[str, bool]:
    saved = await GovernmentSchemeService(db).is_saved(user.id, scheme_id)
    return {"saved": saved}


@router.post("/saved/{scheme_id}", response_model=dict[str, bool])
async def save_scheme(
    scheme_id: int,
    user: CurrentUser,
    db: Db,
) -> dict[str, bool]:
    saved = await GovernmentSchemeService(db).save(user.id, scheme_id)
    if not saved:
        raise HTTPException(status_code=404, detail="Scheme not found.")
    return {"saved": True}


@router.delete("/saved/{scheme_id}", response_model=dict[str, bool])
async def remove_saved_scheme(
    scheme_id: int,
    user: CurrentUser,
    db: Db,
) -> dict[str, bool]:
    removed = await GovernmentSchemeService(db).remove_saved(user.id, scheme_id)
    if not removed:
        raise HTTPException(status_code=404, detail="Saved scheme not found.")
    return {"saved": False}


@router.get("/{scheme_id}", response_model=GovernmentSchemeOut)
async def get_scheme(scheme_id: int, user: CurrentUser, db: Db) -> GovernmentSchemeOut:
    scheme = await GovernmentSchemeService(db).get(user.id, scheme_id)
    if scheme is None:
        raise HTTPException(status_code=404, detail="Scheme not found.")
    return _scheme_out(scheme)


@router.post("/{scheme_id}/eligibility", response_model=EligibilityCheckOut)
async def check_eligibility(
    scheme_id: int,
    payload: EligibilityCheckIn,
    user: CurrentUser,
    db: Db,
) -> EligibilityCheckOut:
    result = await GovernmentSchemeService(db).check_eligibility(
        user.id,
        scheme_id,
        payload,
    )
    if result is None:
        raise HTTPException(status_code=404, detail="Scheme not found.")
    return result


@router.post("", response_model=GovernmentSchemeOut, status_code=201)
async def add_scheme(
    payload: GovernmentSchemeCreate,
    _admin: AdminUser,
    db: Db,
) -> GovernmentSchemeOut:
    """Add externally sourced scheme information; only administrators may curate it."""
    try:
        scheme = await GovernmentSchemeService(db).create(payload)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return _scheme_out(scheme)
