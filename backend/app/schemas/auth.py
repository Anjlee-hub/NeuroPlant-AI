"""Auth & session schemas.

Phone format: E.164-ish (leading ``+`` optional, 8–15 digits). Passwords are
optional so phone-only (OTP) registration stays possible; when set they must
be 6–128 chars.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

PHONE_PATTERN = r"^\+?[1-9]\d{7,14}$"


# ── Requests ─────────────────────────────────────────────────────────────


class RegisterRequest(BaseModel):
    phone: str = Field(pattern=PHONE_PATTERN)
    name: str = Field(min_length=1, max_length=120)
    role: str = Field(default="farmer", min_length=1)
    password: str | None = Field(default=None, min_length=6, max_length=128)
    email: EmailStr | None = None


class LoginRequest(BaseModel):
    identifier: str = Field(min_length=3, max_length=255)  # phone or email
    password: str = Field(min_length=1)


class OtpSendRequest(BaseModel):
    phone: str = Field(pattern=PHONE_PATTERN)
    purpose: str = Field(default="login", pattern=r"^(login|register)$")


class OtpVerifyRequest(BaseModel):
    phone: str = Field(pattern=PHONE_PATTERN)
    purpose: str = Field(default="login", pattern=r"^(login|register)$")
    code: str = Field(min_length=6, max_length=6)


class RefreshRequest(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
    refresh_token: str


class MfaVerifyRequest(BaseModel):
    challenge: str
    code: str = Field(min_length=6, max_length=10)


class MfaConfirmRequest(BaseModel):
    code: str = Field(min_length=6, max_length=6)


# ── Responses ────────────────────────────────────────────────────────────


class TokenResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class MfaChallengeResponse(BaseModel):
    requires_mfa: bool = True
    mfa_challenge: str


class OtpSendResponse(BaseModel):
    message: str
    # Plain code is surfaced to the client only in development so the flow is
    # testable without an SMS provider. Never present in production.
    debug_code: str | None = None


class MfaSetupResponse(BaseModel):
    secret: str
    otpauth_uri: str
    qr_url: str


class MfaCodesResponse(BaseModel):
    backup_codes: list[str]


class DeviceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    device_id: str
    name: str | None
    platform: str | None
    last_seen: datetime
    trusted: bool


class LoginEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    device_id: str | None
    ip: str | None
    user_agent: str | None
    method: str
    success: bool
    mfa_used: bool
    created_at: datetime
