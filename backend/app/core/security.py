"""Security primitives: argon2 password hashing, JWT issuance/verification.

Token model (JWT, HS256):
- access  : short-lived (settings.jwt_access_expire_minutes), type=access
- refresh : longer-lived (settings.jwt_refresh_expire_days), type=refresh,
  random ``jti``; the raw token is never stored — only its SHA-256 hash, so a
  DB leak does not expose usable refresh tokens. Rotation revokes the old row.
"""

import hashlib
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import Argon2Error

from app.core.config import get_settings

_pw_hasher = PasswordHasher()

# ── Passwords ────────────────────────────────────────────────────────────


def hash_password(password: str) -> str:
    return _pw_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _pw_hasher.verify(password_hash, password)
    except (Argon2Error, ValueError):
        return False


# ── JWT ──────────────────────────────────────────────────────────────────


class TokenError(Exception):
    """Raised for invalid, expired or wrong-typed tokens."""


def _now() -> datetime:
    return datetime.now(UTC)


def _encode(payload: dict, secret: str, expires_delta: timedelta) -> str:
    now = _now()
    full = {**payload, "iat": now, "exp": now + expires_delta, "nbf": now}
    return jwt.encode(full, secret, algorithm=get_settings().jwt_algorithm)


def create_access_token(user_id: int, role: str) -> tuple[str, str]:
    """Returns ``(token, jti)`` for an access token."""
    jti = str(uuid4())
    payload = {"sub": str(user_id), "role": role, "type": "access", "jti": jti}
    settings = get_settings()
    token = _encode(
        payload,
        settings.jwt_secret,
        timedelta(minutes=settings.jwt_access_expire_minutes),
    )
    return token, jti


def create_refresh_token(user_id: int, jti: str) -> str:
    payload = {"sub": str(user_id), "type": "refresh", "jti": jti}
    settings = get_settings()
    return _encode(
        payload,
        settings.jwt_refresh_secret,
        timedelta(days=settings.jwt_refresh_expire_days),
    )


def decode_token(token: str, *, secret: str, expected_type: str) -> dict:
    settings = get_settings()
    try:
        payload = jwt.decode(
            token,
            secret,
            algorithms=[settings.jwt_algorithm],
            options={"require": ["sub", "exp", "type"]},
        )
    except jwt.PyJWTError as exc:
        raise TokenError("invalid token") from exc
    if payload.get("type") != expected_type:
        raise TokenError("wrong token type")
    return payload


def decode_access_token(token: str) -> dict:
    return decode_token(token, secret=get_settings().jwt_secret, expected_type="access")


def decode_refresh_token(token: str) -> dict:
    return decode_token(token, secret=get_settings().jwt_refresh_secret, expected_type="refresh")


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()
