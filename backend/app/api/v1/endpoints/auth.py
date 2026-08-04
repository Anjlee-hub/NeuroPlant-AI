"""Auth endpoints: registration, login (password / OTP / MFA), token
rotation, devices and login history.

Service-layer exceptions (``AuthError`` subclasses, ``OtpError``) propagate to
app-level handlers registered in ``main.py``.
"""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_current_user, get_device_info
from app.core.config import get_settings
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import (
    DeviceOut,
    LoginEventOut,
    LoginRequest,
    LogoutRequest,
    MfaChallengeResponse,
    MfaCodesResponse,
    MfaConfirmRequest,
    MfaSetupResponse,
    MfaVerifyRequest,
    OtpSendRequest,
    OtpSendResponse,
    OtpVerifyRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
)
from app.schemas.user import UserOut
from app.services import auth as auth_svc
from app.services.auth import DeviceInfo, MfaRequiredError
from app.services.otp import send_otp, verify_otp

router = APIRouter(prefix="/auth", tags=["auth"])

Db = Annotated[AsyncSession, Depends(get_db)]
Device = Annotated[DeviceInfo, Depends(get_device_info)]
CurrentUser = Annotated[User, Depends(get_current_user)]


@router.post("/register", response_model=TokenResponse, status_code=201)
async def register(payload: RegisterRequest, db: Db, device: Device) -> TokenResponse:
    user = await auth_svc.register_user(
        db,
        phone=payload.phone,
        name=payload.name,
        role=payload.role,
        password=payload.password,
        email=str(payload.email) if payload.email else None,
    )
    pair = await auth_svc.issue_tokens(db, user, device)
    return TokenResponse(access_token=pair.access_token, refresh_token=pair.refresh_token)


@router.post("/login", response_model=TokenResponse | MfaChallengeResponse)
async def login(
    payload: LoginRequest, db: Db, device: Device
) -> TokenResponse | MfaChallengeResponse:
    result = await auth_svc.password_login(db, payload.identifier, payload.password, device)
    if isinstance(result, MfaRequiredError):
        return MfaChallengeResponse(mfa_challenge=result.challenge)
    return TokenResponse(access_token=result.access_token, refresh_token=result.refresh_token)


@router.post("/otp/send", response_model=OtpSendResponse)
async def otp_send(payload: OtpSendRequest, db: Db) -> OtpSendResponse:
    code = await send_otp(db, payload.phone, payload.purpose)
    return OtpSendResponse(
        message="OTP sent",
        debug_code=code if get_settings().debug else None,
    )


@router.post("/otp/verify", response_model=TokenResponse)
async def otp_verify(payload: OtpVerifyRequest, db: Db, device: Device) -> TokenResponse:
    await verify_otp(db, payload.phone, payload.purpose, payload.code)
    pair = await auth_svc.otp_login(db, payload.phone, device)
    return TokenResponse(access_token=pair.access_token, refresh_token=pair.refresh_token)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(payload: RefreshRequest, db: Db, device: Device) -> TokenResponse:
    pair = await auth_svc.refresh(db, payload.refresh_token, device)
    return TokenResponse(access_token=pair.access_token, refresh_token=pair.refresh_token)


@router.post("/logout", status_code=204)
async def logout(payload: LogoutRequest, db: Db) -> None:
    await auth_svc.logout(db, payload.refresh_token)


@router.get("/me", response_model=UserOut)
async def me(current_user: CurrentUser) -> User:
    return current_user


# ── MFA ──────────────────────────────────────────────────────────────────


@router.post("/mfa/setup", response_model=MfaSetupResponse)
async def mfa_setup(db: Db, current_user: CurrentUser) -> MfaSetupResponse:
    return MfaSetupResponse(**await auth_svc.setup_mfa(db, current_user.id))


@router.post("/mfa/confirm", response_model=MfaCodesResponse)
async def mfa_confirm(
    payload: MfaConfirmRequest, db: Db, current_user: CurrentUser
) -> MfaCodesResponse:
    codes = await auth_svc.confirm_mfa(db, current_user.id, payload.code)
    return MfaCodesResponse(backup_codes=codes)


@router.post("/mfa/backup-codes", response_model=MfaCodesResponse)
async def mfa_backup_codes(db: Db, current_user: CurrentUser) -> MfaCodesResponse:
    codes = await auth_svc.regenerate_backup_codes(db, current_user.id)
    return MfaCodesResponse(backup_codes=codes)


@router.post("/mfa/verify", response_model=TokenResponse)
async def mfa_verify(payload: MfaVerifyRequest, db: Db, device: Device) -> TokenResponse:
    pair = await auth_svc.confirm_mfa_challenge(db, payload.challenge, payload.code, device)
    return TokenResponse(access_token=pair.access_token, refresh_token=pair.refresh_token)


# ── Devices & sessions ───────────────────────────────────────────────────


@router.get("/devices", response_model=list[DeviceOut])
async def devices(db: Db, current_user: CurrentUser) -> list:
    return await auth_svc.list_devices(db, current_user.id)


@router.delete("/devices/{device_id}", status_code=204)
async def delete_device(device_id: str, db: Db, current_user: CurrentUser) -> None:
    await auth_svc.revoke_device(db, current_user.id, device_id)


@router.get("/sessions", response_model=list[LoginEventOut])
async def sessions(db: Db, current_user: CurrentUser) -> list:
    return await auth_svc.list_login_history(db, current_user.id)
