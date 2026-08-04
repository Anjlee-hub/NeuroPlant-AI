"""Authentication & session service.

Responsibilities: registration, password + OTP login, MFA (TOTP + backup
codes), refresh-token rotation with reuse detection, device management, login
history.
"""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from secrets import token_urlsafe
from uuid import uuid4

import pyotp
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.logging import get_logger
from app.core.security import (
    TokenError,
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
    hash_password,
    hash_token,
    verify_password,
)
from app.db.session import ensure_aware
from app.models.base import UserRole
from app.models.user import (
    MFA,
    Device,
    ExpertProfile,
    FarmerProfile,
    LoginEvent,
    RefreshToken,
    SellerProfile,
    User,
)

logger = get_logger("services.auth")

MFA_CHALLENGE_TTL_MINUTES = 10
BACKUP_CODE_COUNT = 10


class AuthError(Exception):
    """Base auth failure (mapped to 401/400 in the API layer)."""


class UserExistsError(AuthError):
    """Phone/email already registered."""


class UserNotFoundError(AuthError):
    pass


class InvalidCredentialsError(AuthError):
    pass


class MfaRequiredError(AuthError):
    """Password correct, but a second factor is required."""

    def __init__(self, challenge: str):
        super().__init__("MFA required")
        self.challenge = challenge


class InvalidMfaError(AuthError):
    pass


class MfaNotEnabledError(AuthError):
    pass


@dataclass
class DeviceInfo:
    device_id: str | None = None
    name: str | None = None
    platform: str | None = None
    ip: str | None = None
    user_agent: str | None = None


@dataclass
class TokenPair:
    access_token: str
    refresh_token: str


# ── Registration ─────────────────────────────────────────────────────────


async def register_user(
    db: AsyncSession,
    *,
    phone: str,
    name: str,
    role: str,
    password: str | None,
    email: str | None = None,
) -> User:
    if role not in UserRole.ALL:
        raise AuthError(f"invalid role: {role}")
    existing = await db.scalar(select(User).where(User.phone == phone))
    if existing:
        raise UserExistsError("phone already registered")
    if email:
        email_user = await db.scalar(select(User).where(User.email == email))
        if email_user:
            raise UserExistsError("email already registered")

    password_hash = hash_password(password) if password else None
    user = User(
        phone=phone,
        email=email,
        name=name,
        role=role,
        password_hash=password_hash,
    )
    db.add(user)
    await db.flush()

    # Role-specific profile.
    if role == UserRole.FARMER:
        db.add(FarmerProfile(user_id=user.id))
    elif role == UserRole.EXPERT:
        db.add(ExpertProfile(user_id=user.id))
    elif role == UserRole.SELLER:
        db.add(SellerProfile(user_id=user.id))

    await db.commit()
    await db.refresh(user)
    logger.info("user_registered", user_id=user.id, role=role)
    return user


# ── Password login ───────────────────────────────────────────────────────


async def password_login(
    db: AsyncSession, identifier: str, password: str, device: DeviceInfo
) -> TokenPair | MfaRequiredError:
    user = await _find_by_identifier(db, identifier)
    if user is None or not user.password_hash:
        await _record_login(db, None, device, success=False, method="password")
        raise InvalidCredentialsError("invalid credentials")
    if not verify_password(password, user.password_hash):
        await _record_login(db, user.id, device, success=False, method="password")
        raise InvalidCredentialsError("invalid credentials")

    mfa = await _get_mfa(db, user.id)
    if mfa and mfa.enabled:
        challenge = _create_mfa_challenge(user)
        await _record_login(db, user.id, device, success=True, method="password")
        return MfaRequiredError(challenge)

    await _record_login(db, user.id, device, success=True, method="password")
    return await _issue_tokens(db, user, device)


async def _find_by_identifier(db: AsyncSession, identifier: str) -> User | None:
    if "@" in identifier:
        return await db.scalar(select(User).where(User.email == identifier))
    return await db.scalar(select(User).where(User.phone == identifier))


# ── OTP login ────────────────────────────────────────────────────────────


async def otp_login(db: AsyncSession, phone: str, device: DeviceInfo) -> TokenPair:
    user = await db.scalar(select(User).where(User.phone == phone))
    if user is None:
        raise UserNotFoundError("no account for this phone — register first")
    await _record_login(db, user.id, device, success=True, method="otp")
    return await _issue_tokens(db, user, device)


# ── MFA ──────────────────────────────────────────────────────────────────


async def setup_mfa(db: AsyncSession, user_id: int) -> dict:
    """Create a TOTP secret (idempotent). Returns provisioning data."""
    mfa = await _get_mfa(db, user_id)
    if mfa is None:
        secret = pyotp.random_base32()
        mfa = MFA(user_id=user_id, totp_secret=secret, enabled=False)
        db.add(mfa)
        await db.commit()
        await db.refresh(mfa)
    if mfa.enabled:
        raise MfaNotEnabledError("MFA is already enabled")

    user = await db.get(User, user_id)
    if user is None:
        raise AuthError("user not found")
    totp = pyotp.TOTP(mfa.totp_secret)
    provisioning_uri = totp.provisioning_uri(name=user.phone, issuer_name="NeuroPlant AI")
    return {
        "secret": mfa.totp_secret,
        "otpauth_uri": provisioning_uri,
        "qr_url": f"https://api.qrserver.com/v1/create-qr-code/?data={provisioning_uri}",
    }


async def confirm_mfa(db: AsyncSession, user_id: int, code: str) -> list[str]:
    """Enable MFA after verifying the TOTP code. Returns backup codes."""
    mfa = await _get_mfa(db, user_id)
    if mfa is None or not _totp_verify(mfa.totp_secret, code):
        raise InvalidMfaError("invalid TOTP code")
    mfa.enabled = True
    codes = [token_urlsafe(5).replace("-", "") for _ in range(BACKUP_CODE_COUNT)]
    mfa.backup_codes_hash = [hash_token(c) for c in codes]
    await db.commit()
    logger.info("mfa_enabled", user_id=user_id)
    return codes


async def regenerate_backup_codes(db: AsyncSession, user_id: int) -> list[str]:
    """Replace an enabled user's backup codes (old codes stop working)."""
    mfa = await _get_mfa(db, user_id)
    if mfa is None or not mfa.enabled:
        raise MfaNotEnabledError("MFA is not enabled")
    codes = [token_urlsafe(5).replace("-", "") for _ in range(BACKUP_CODE_COUNT)]
    mfa.backup_codes_hash = [hash_token(c) for c in codes]
    await db.commit()
    logger.info("mfa_backup_codes_regenerated", user_id=user_id)
    return codes


async def confirm_mfa_challenge(
    db: AsyncSession, challenge: str, code: str, device: DeviceInfo
) -> TokenPair:
    """Complete a password+MFA login: verify challenge-bound user + code."""
    user_id = _read_mfa_challenge(challenge)
    if user_id is None:
        raise InvalidMfaError("invalid or expired challenge")
    user = await db.get(User, user_id)
    if user is None:
        raise InvalidMfaError("user not found")
    mfa = await _get_mfa(db, user_id)
    if mfa is None or not mfa.enabled:
        raise InvalidMfaError("MFA not enabled")

    if _totp_verify(mfa.totp_secret, code):
        await _record_login(db, user_id, device, success=True, method="mfa_totp", mfa_used=True)
        return await _issue_tokens(db, user, device)

    # Fall back to a backup code. Single-use: reassign the list so the change
    # is persisted — in-place mutation of a JSON column is not tracked by the
    # ORM, which would let a consumed code be replayed.
    if mfa.backup_codes_hash:
        for i, code_hash in enumerate(mfa.backup_codes_hash):
            if hash_token(code) == code_hash:
                mfa.backup_codes_hash = [c for j, c in enumerate(mfa.backup_codes_hash) if j != i]
                await db.commit()
                await _record_login(
                    db, user_id, device, success=True, method="mfa_backup", mfa_used=True
                )
                return await _issue_tokens(db, user, device)
    raise InvalidMfaError("invalid code")


# ── Token issuance & rotation ────────────────────────────────────────────


async def issue_tokens(db: AsyncSession, user: User, device: DeviceInfo) -> TokenPair:
    """Public token issuance (auto-login after registration, etc.)."""
    return await _issue_tokens(db, user, device)


async def _issue_tokens(db: AsyncSession, user: User, device: DeviceInfo) -> TokenPair:
    access, _ = create_access_token(user.id, user.role)
    refresh_jti = str(uuid4())
    refresh = create_refresh_token(user.id, refresh_jti)

    db.add(
        RefreshToken(
            user_id=user.id,
            token_hash=hash_token(refresh),
            jti=refresh_jti,
            expires_at=datetime.now(UTC) + timedelta(days=get_settings().jwt_refresh_expire_days),
            device_id=device.device_id,
        )
    )
    await _upsert_device(db, user.id, device)
    await db.commit()
    return TokenPair(access_token=access, refresh_token=refresh)


async def refresh(db: AsyncSession, refresh_token: str, device: DeviceInfo) -> TokenPair:
    """Rotate a refresh token; detect and punish reuse."""
    try:
        payload = decode_refresh_token(refresh_token)
    except TokenError as exc:
        raise InvalidCredentialsError("invalid refresh token") from exc

    user_id = int(payload["sub"])
    row = await db.scalar(
        select(RefreshToken).where(RefreshToken.token_hash == hash_token(refresh_token))
    )
    if row is None:
        raise InvalidCredentialsError("unknown refresh token")

    if row.revoked_at is not None:
        # Reuse of a rotated token — likely theft. Revoke the whole session family.
        logger.warning("refresh_token_reuse", user_id=user_id, jti=row.jti)
        await db.execute(delete(RefreshToken).where(RefreshToken.user_id == user_id))
        await db.commit()
        raise InvalidCredentialsError("refresh token revoked")

    if ensure_aware(row.expires_at) < datetime.now(UTC):
        raise InvalidCredentialsError("refresh token expired")

    user = await db.get(User, user_id)
    if user is None:
        raise InvalidCredentialsError("user not found")

    # Rotate: revoke the old token, issue a fresh family member.
    row.revoked_at = datetime.now(UTC)
    access, _ = create_access_token(user.id, user.role)
    new_jti = str(uuid4())
    new_refresh = create_refresh_token(user.id, new_jti)
    db.add(
        RefreshToken(
            user_id=user.id,
            token_hash=hash_token(new_refresh),
            jti=new_jti,
            expires_at=datetime.now(UTC) + timedelta(days=get_settings().jwt_refresh_expire_days),
            rotated_from_jti=row.jti,
            device_id=device.device_id or row.device_id,
        )
    )
    await _upsert_device(db, user.id, device)
    await db.commit()
    return TokenPair(access_token=access, refresh_token=new_refresh)


async def logout(db: AsyncSession, refresh_token: str) -> None:
    try:
        decode_refresh_token(refresh_token)
    except TokenError as exc:
        raise InvalidCredentialsError("invalid refresh token") from exc
    row = await db.scalar(
        select(RefreshToken).where(RefreshToken.token_hash == hash_token(refresh_token))
    )
    if row is not None:
        row.revoked_at = datetime.now(UTC)
        await db.commit()


# ── Devices & login history ──────────────────────────────────────────────


async def list_devices(db: AsyncSession, user_id: int) -> list[Device]:
    result = await db.execute(
        select(Device).where(Device.user_id == user_id).order_by(Device.last_seen.desc())
    )
    return list(result.scalars())


async def revoke_device(db: AsyncSession, user_id: int, device_id: str) -> None:
    await db.execute(delete(Device).where(Device.user_id == user_id, Device.device_id == device_id))
    # Revoke refresh tokens bound to the device too.
    await db.execute(
        delete(RefreshToken).where(
            RefreshToken.user_id == user_id, RefreshToken.device_id == device_id
        )
    )
    await db.commit()


async def list_login_history(db: AsyncSession, user_id: int, limit: int = 20) -> list[LoginEvent]:
    result = await db.execute(
        select(LoginEvent)
        .where(LoginEvent.user_id == user_id)
        .order_by(LoginEvent.id.desc())
        .limit(limit)
    )
    return list(result.scalars())


# ── Internal helpers ─────────────────────────────────────────────────────


async def _get_mfa(db: AsyncSession, user_id: int) -> MFA | None:
    return await db.scalar(select(MFA).where(MFA.user_id == user_id))


def _totp_verify(secret: str, code: str) -> bool:
    return pyotp.TOTP(secret).verify(code, valid_window=1)


def _create_mfa_challenge(user: User) -> str:
    """Signed one-time challenge binding the user to a pending MFA confirm."""
    import jwt  # local import to avoid clashing with app.core.security naming

    settings = get_settings()
    payload = {
        "sub": str(user.id),
        "type": "mfa_challenge",
        "exp": datetime.now(UTC) + timedelta(minutes=MFA_CHALLENGE_TTL_MINUTES),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def _read_mfa_challenge(challenge: str) -> int | None:
    import jwt

    settings = get_settings()
    try:
        payload = jwt.decode(challenge, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except jwt.PyJWTError:
        return None
    if payload.get("type") != "mfa_challenge":
        return None
    try:
        return int(payload["sub"])
    except (KeyError, ValueError):
        return None


async def _upsert_device(db: AsyncSession, user_id: int, device: DeviceInfo) -> None:
    if not device.device_id:
        return
    existing = await db.scalar(
        select(Device).where(Device.user_id == user_id, Device.device_id == device.device_id)
    )
    if existing:
        existing.last_seen = datetime.now(UTC)
        existing.name = device.name or existing.name
        existing.platform = device.platform or existing.platform
    else:
        db.add(
            Device(
                user_id=user_id,
                device_id=device.device_id,
                name=device.name,
                platform=device.platform,
                last_seen=datetime.now(UTC),
            )
        )


async def _record_login(
    db: AsyncSession,
    user_id: int | None,
    device: DeviceInfo,
    *,
    success: bool,
    method: str,
    mfa_used: bool = False,
) -> None:
    db.add(
        LoginEvent(
            user_id=user_id,
            device_id=device.device_id,
            ip=device.ip,
            user_agent=device.user_agent,
            method=method,
            success=success,
            mfa_used=mfa_used,
        )
    )
    await db.commit()
