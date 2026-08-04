"""Shared API dependencies: authentication, RBAC, device fingerprinting.

Routes that need an identity depend on ``get_current_user`` (a ``User``
model). ``require_roles`` returns a dependency that also enforces role access.
"""

from collections.abc import Awaitable, Callable

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import TokenError, decode_access_token
from app.db.session import get_db
from app.models.user import User
from app.services.auth import DeviceInfo

_bearer = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Resolve the authenticated user from the access-token bearer header."""
    if credentials is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="not authenticated")
    try:
        payload = decode_access_token(credentials.credentials)
    except TokenError as exc:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, detail="invalid or expired token"
        ) from exc

    user = await db.get(User, int(payload["sub"]))
    if user is None or user.status != "active":
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="user not found or inactive")
    return user


def require_roles(*roles: str) -> Callable[..., Awaitable[User]]:
    """Build a dependency that allows only the given roles."""

    async def _check(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail="insufficient permissions")
        return user

    return _check


def get_device_info(request: Request) -> DeviceInfo:
    """Build device fingerprint from headers (sent by the client on login)."""
    return DeviceInfo(
        device_id=request.headers.get("X-Device-Id"),
        name=request.headers.get("X-Device-Name"),
        platform=request.headers.get("X-Device-Platform"),
        ip=request.client.host if request.client else None,
        user_agent=request.headers.get("User-Agent"),
    )
