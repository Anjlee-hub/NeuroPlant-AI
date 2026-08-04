"""Auth & session integration tests (M1).

Covers: registration (+ role profiles + uniqueness), password login, refresh
token rotation + reuse detection, logout, OTP login, MFA (TOTP + backup codes),
device management, login history, and RBAC/current-user protection.
"""

import pyotp

PHONE = "+919000000001"
PASSWORD = "secret123"

FARMER_HEADERS = {
    "X-Device-Id": "dev-android-1",
    "X-Device-Name": "Pixel 8",
    "X-Device-Platform": "android",
}


async def _register(
    client, *, phone=PHONE, role="farmer", password=PASSWORD, headers=FARMER_HEADERS
):
    resp = await client.post(
        "/api/v1/auth/register",
        json={"phone": phone, "name": "Test User", "role": role, "password": password},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def _bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


# ── Registration ─────────────────────────────────────────────────────────


async def test_register_returns_tokens(client):
    body = await _register(client)
    assert body["access_token"]
    assert body["refresh_token"]
    assert body["token_type"] == "bearer"


async def test_register_creates_role_profile(client):
    from app.db.session import async_session_factory
    from app.models import FarmerProfile
    from sqlalchemy import select

    await _register(client, role="farmer")
    async with async_session_factory() as db:
        profile = await db.scalar(select(FarmerProfile))
        assert profile is not None


async def test_register_duplicate_phone_conflict(client):
    await _register(client)
    resp = await client.post(
        "/api/v1/auth/register",
        json={"phone": PHONE, "name": "Other", "role": "customer", "password": PASSWORD},
    )
    assert resp.status_code == 409


async def test_register_invalid_role_rejected(client):
    resp = await client.post(
        "/api/v1/auth/register",
        json={"phone": PHONE, "name": "X", "role": "superuser", "password": PASSWORD},
    )
    assert resp.status_code == 400


# ── Password login ───────────────────────────────────────────────────────


async def test_password_login_ok(client):
    await _register(client)
    resp = await client.post(
        "/api/v1/auth/login",
        json={"identifier": PHONE, "password": PASSWORD},
        headers=FARMER_HEADERS,
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["access_token"]


async def test_password_login_wrong_password(client):
    await _register(client)
    resp = await client.post(
        "/api/v1/auth/login",
        json={"identifier": PHONE, "password": "wrong-password"},
    )
    assert resp.status_code == 401


async def test_password_login_unknown_user(client):
    resp = await client.post(
        "/api/v1/auth/login",
        json={"identifier": "+919999999999", "password": PASSWORD},
    )
    assert resp.status_code == 401


# ── Refresh token rotation & reuse detection ─────────────────────────────


async def test_refresh_rotation_rotates_token(client):
    reg = await _register(client)
    first = reg["refresh_token"]

    # Rotate forward twice — each rotation issues a distinct token.
    resp = await client.post("/api/v1/auth/refresh", json={"refresh_token": first})
    assert resp.status_code == 200, resp.text
    second = resp.json()["refresh_token"]
    assert second != first

    resp = await client.post("/api/v1/auth/refresh", json={"refresh_token": second})
    assert resp.status_code == 200, resp.text
    third = resp.json()["refresh_token"]
    assert third != second


async def test_refresh_reuse_revokes_session_family(client):
    reg = await _register(client)
    first = reg["refresh_token"]

    resp = await client.post("/api/v1/auth/refresh", json={"refresh_token": first})
    assert resp.status_code == 200
    second = resp.json()["refresh_token"]

    # Reuse of a rotated token is treated as theft: the whole family dies.
    resp = await client.post("/api/v1/auth/refresh", json={"refresh_token": first})
    assert resp.status_code == 401
    resp = await client.post("/api/v1/auth/refresh", json={"refresh_token": second})
    assert resp.status_code == 401


async def test_logout_revokes_refresh_token(client):
    reg = await _register(client)
    resp = await client.post("/api/v1/auth/logout", json={"refresh_token": reg["refresh_token"]})
    assert resp.status_code == 204

    resp = await client.post("/api/v1/auth/refresh", json={"refresh_token": reg["refresh_token"]})
    assert resp.status_code == 401


# ── OTP login ────────────────────────────────────────────────────────────


async def test_otp_login_flow(client):
    await _register(client)

    sent = await client.post("/api/v1/auth/otp/send", json={"phone": PHONE})
    assert sent.status_code == 200, sent.text
    code = sent.json()["debug_code"]
    assert code and len(code) == 6

    resp = await client.post(
        "/api/v1/auth/otp/verify",
        json={"phone": PHONE, "purpose": "login", "code": code},
        headers=FARMER_HEADERS,
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["access_token"]


async def test_otp_single_use(client):
    await _register(client)
    code = (await client.post("/api/v1/auth/otp/send", json={"phone": PHONE})).json()["debug_code"]

    first = await client.post(
        "/api/v1/auth/otp/verify",
        json={"phone": PHONE, "purpose": "login", "code": code},
    )
    assert first.status_code == 200

    # Same code cannot be replayed.
    second = await client.post(
        "/api/v1/auth/otp/verify",
        json={"phone": PHONE, "purpose": "login", "code": code},
    )
    assert second.status_code == 400


async def test_otp_wrong_code(client):
    await _register(client)
    resp = await client.post(
        "/api/v1/auth/otp/verify",
        json={"phone": PHONE, "purpose": "login", "code": "000000"},
    )
    assert resp.status_code == 400


# ── MFA (TOTP + backup codes) ────────────────────────────────────────────


async def _enable_mfa(client, token):
    headers = _bearer(token)
    setup = await client.post("/api/v1/auth/mfa/setup", headers=headers)
    assert setup.status_code == 200, setup.text
    secret = setup.json()["secret"]
    totp_code = pyotp.TOTP(secret).now()

    confirm = await client.post(
        "/api/v1/auth/mfa/confirm", json={"code": totp_code}, headers=headers
    )
    assert confirm.status_code == 200, confirm.text
    return confirm.json()["backup_codes"]


async def test_mfa_setup_confirm_and_challenge_login(client):
    reg = await _register(client)
    await _enable_mfa(client, reg["access_token"])

    # Password login now returns an MFA challenge instead of tokens.
    login = await client.post(
        "/api/v1/auth/login", json={"identifier": PHONE, "password": PASSWORD}
    )
    assert login.status_code == 200
    body = login.json()
    assert body["requires_mfa"] is True
    assert body["mfa_challenge"]
    assert "access_token" not in body


async def test_mfa_challenge_verify_with_totp(client):
    from app.db.session import async_session_factory
    from app.models import MFA
    from sqlalchemy import select

    reg = await _register(client)
    await _enable_mfa(client, reg["access_token"])

    async with async_session_factory() as db:
        mfa = await db.scalar(select(MFA))
        secret = mfa.totp_secret

    login = await client.post(
        "/api/v1/auth/login", json={"identifier": PHONE, "password": PASSWORD}
    )
    challenge = login.json()["mfa_challenge"]

    resp = await client.post(
        "/api/v1/auth/mfa/verify",
        json={"challenge": challenge, "code": pyotp.TOTP(secret).now()},
        headers=FARMER_HEADERS,
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["access_token"]


async def test_mfa_backup_code_login(client):
    from app.db.session import async_session_factory
    from app.models import MFA
    from sqlalchemy import select

    reg = await _register(client)
    backup_codes = await _enable_mfa(client, reg["access_token"])
    backup_code = backup_codes[0]

    login = await client.post(
        "/api/v1/auth/login", json={"identifier": PHONE, "password": PASSWORD}
    )
    challenge = login.json()["mfa_challenge"]

    resp = await client.post(
        "/api/v1/auth/mfa/verify",
        json={"challenge": challenge, "code": backup_code},
        headers=FARMER_HEADERS,
    )
    assert resp.status_code == 200, resp.text

    # Backup codes are single-use — the same code must now fail.
    login = await client.post(
        "/api/v1/auth/login", json={"identifier": PHONE, "password": PASSWORD}
    )
    resp = await client.post(
        "/api/v1/auth/mfa/verify",
        json={"challenge": login.json()["mfa_challenge"], "code": backup_code},
    )
    assert resp.status_code == 400

    # A fresh TOTP code still works after a backup-code login.
    async with async_session_factory() as db:
        secret = (await db.scalar(select(MFA))).totp_secret
    resp = await client.post(
        "/api/v1/auth/mfa/verify",
        json={"challenge": login.json()["mfa_challenge"], "code": pyotp.TOTP(secret).now()},
        headers=FARMER_HEADERS,
    )
    assert resp.status_code == 200


# ── Devices & login history ──────────────────────────────────────────────


async def test_device_registration_and_revocation(client):
    reg = await _register(client, headers=FARMER_HEADERS)
    headers = {"Authorization": f"Bearer {reg['access_token']}"}

    devices = await client.get("/api/v1/auth/devices", headers=headers)
    assert devices.status_code == 200
    body = devices.json()
    assert len(body) == 1
    assert body[0]["device_id"] == "dev-android-1"

    resp = await client.delete("/api/v1/auth/devices/dev-android-1", headers=headers)
    assert resp.status_code == 204

    devices = await client.get("/api/v1/auth/devices", headers=headers)
    assert devices.json() == []


async def test_login_history_recorded(client):
    reg = await _register(client)
    await client.post("/api/v1/auth/login", json={"identifier": PHONE, "password": PASSWORD})

    sessions = await client.get("/api/v1/auth/sessions", headers=_bearer(reg["access_token"]))
    assert sessions.status_code == 200
    events = sessions.json()
    assert len(events) >= 1
    assert events[0]["method"] == "password"
    assert events[0]["success"] is True


# ── Current-user & RBAC ──────────────────────────────────────────────────


async def test_me_requires_auth(client):
    resp = await client.get("/api/v1/auth/me")
    assert resp.status_code == 401


async def test_me_rejects_garbage_token(client):
    resp = await client.get("/api/v1/auth/me", headers={"Authorization": "Bearer not-a-jwt"})
    assert resp.status_code == 401


async def test_me_returns_identity(client):
    reg = await _register(client)
    resp = await client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {reg['access_token']}"}
    )
    assert resp.status_code == 200
    assert resp.json()["phone"] == PHONE
    assert resp.json()["role"] == "farmer"


async def test_update_profile(client):
    reg = await _register(client)
    headers = {"Authorization": f"Bearer {reg['access_token']}"}
    resp = await client.patch("/api/v1/users/me", json={"name": "Renamed Farmer"}, headers=headers)
    assert resp.status_code == 200
    assert resp.json()["name"] == "Renamed Farmer"
