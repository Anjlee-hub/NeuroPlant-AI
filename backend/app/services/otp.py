"""One-time passcode (OTP) service.

Codes are 6 digits, hashed at rest, single-use, with an attempt counter and a
short TTL. In production the plain code is delivered by an SMS adapter (wired
later); in development it is surfaced so the flow is fully testable without an
SMS provider.
"""

import hashlib
import secrets
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.logging import get_logger
from app.db.session import ensure_aware
from app.models.user import OtpCode

logger = get_logger("services.otp")

OTP_TTL_MINUTES = 5
OTP_MAX_ATTEMPTS = 5


def _hash(code: str) -> str:
    return hashlib.sha256(code.encode()).hexdigest()


def _now() -> datetime:
    return datetime.now(UTC)


class OtpError(Exception):
    """OTP invalid/expired/rate-limited."""


async def send_otp(db: AsyncSession, phone: str, purpose: str = "login") -> str:
    """Create + "deliver" an OTP. Returns the plain code (dev: shown to client)."""
    code = f"{secrets.randbelow(1_000_000):06d}"
    db.add(
        OtpCode(
            phone=phone,
            purpose=purpose,
            code_hash=_hash(code),
            expires_at=_now() + timedelta(minutes=OTP_TTL_MINUTES),
        )
    )
    await db.commit()

    settings = get_settings()
    if settings.debug:
        logger.info("otp_delivered_dev", phone=phone, purpose=purpose, code=code)
    else:
        # TODO(M2): SMS/WhatsApp provider adapter.
        logger.info("otp_queued_for_sms", phone=phone, purpose=purpose)

    return code


async def verify_otp(db: AsyncSession, phone: str, purpose: str, code: str) -> bool:
    """Verify the latest unconsumed code for (phone, purpose). Single-use."""
    result = await db.execute(
        select(OtpCode)
        .where(
            OtpCode.phone == phone,
            OtpCode.purpose == purpose,
            OtpCode.used.is_(False),
        )
        .order_by(OtpCode.id.desc())
        .limit(1)
    )
    record = result.scalar_one_or_none()
    if record is None:
        raise OtpError("no active code for this phone")

    if ensure_aware(record.expires_at) < _now():
        raise OtpError("code expired")

    if record.attempts >= OTP_MAX_ATTEMPTS:
        raise OtpError("too many attempts — request a new code")

    if not secrets.compare_digest(record.code_hash, _hash(code)):
        record.attempts += 1
        await db.commit()
        raise OtpError("incorrect code")

    record.used = True
    record.attempts += 1
    await db.commit()
    return True
