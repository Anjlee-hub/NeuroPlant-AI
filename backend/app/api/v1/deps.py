"""Shared API dependencies: authentication, RBAC, device fingerprinting.

Routes that need an identity depend on ``get_current_user`` (a ``User``
model). ``require_roles`` returns a dependency that also enforces role access.
"""

from collections.abc import Awaitable, Callable

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rate_limit import (
    get_message_limiter,
    get_scan_limiter,
    get_scan_sync_limiter,
)
from app.core.security import TokenError, decode_access_token
from app.db.session import get_db
from app.models.user import User
from app.services.auth import DeviceInfo
from app.services.detection import DetectionService

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


async def get_detection_service(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> DetectionService:
    """Build the detection stack once per process (cached on ``app.state``).

    The expensive work (label catalog + classifier registration) is lazy inside
    :meth:`DetectionService.build`; caching it on the app state avoids rebuilding
    for every upload. Tests reset the cache between cases for isolation.
    """
    cached = getattr(request.app.state, "detection_service", None)
    if cached is None:
        cached = await DetectionService.build(db)
        request.app.state.detection_service = cached
    return cached


async def scan_upload_rate_limit(
    request: Request,
    user: User = Depends(get_current_user),
) -> None:
    """Dependency: one scan-upload slot per user+IP per minute (when enabled).

    Keyed by user id plus client IP so a shared account on one network shares a
    single budget without letting any one client bypass the quota.
    """
    limiter = get_scan_limiter()
    client_ip = request.client.host if request.client else "?"
    if not limiter.allow(f"scan:{user.id}:{client_ip}"):
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            detail="too many scan uploads, please try again shortly",
        )


async def scan_sync_rate_limit(
    request: Request,
    user: User = Depends(get_current_user),
) -> None:
    """Dependency: one sync-batch slot per user+IP per minute (when enabled).

    Offline drain is a burst-heavy operation, so it gets its own budget
    (``rate_limit_scan_sync_per_minute``) rather than competing with live
    uploads for ``scan`` tokens.
    """
    limiter = get_scan_sync_limiter()
    client_ip = request.client.host if request.client else "?"
    if not limiter.allow(f"scan-sync:{user.id}:{client_ip}"):
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            detail="too many scan syncs, please try again shortly",
        )


async def message_rate_limit(
    request: Request,
    user: User = Depends(get_current_user),
) -> None:
    """Dependency: one marketplace message slot per user+IP per minute (M4 T5).

    Bounds chat spam while keeping the surface open in dev (the limiter is a
    no-op when ``rate_limit_enabled`` is False). Applies to both thread creation
    (the opening message) and each reply.
    """
    limiter = get_message_limiter()
    client_ip = request.client.host if request.client else "?"
    if not limiter.allow(f"message:{user.id}:{client_ip}"):
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            detail="too many messages, please try again shortly",
        )
