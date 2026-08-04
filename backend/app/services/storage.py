"""Object-storage abstraction.

The scan pipeline talks to :class:`StorageService` only, so swapping local
disk for S3/R2/MinIO later is a config change (``settings.storage_provider``),
not a code change. Keys are relative, user-scoped and content-addressed
(random hex), never client-supplied — no path traversal or name collisions.
"""

from __future__ import annotations

import secrets
from pathlib import Path
from typing import Protocol

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# Declared MIME → safe extension (storage never trusts client extensions).
_EXTENSIONS: dict[str, str] = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
    "image/bmp": "bmp",
    "image/gif": "gif",
    "image/tiff": "tiff",
}


class StorageService(Protocol):
    """Persist and retrieve opaque media blobs under a relative key."""

    def save(self, data: bytes, content_type: str, user_id: int, subdir: str = "") -> str:
        """Write ``data`` and return the relative storage key."""
        ...

    def delete(self, key: str) -> None:
        """Remove the blob at ``key`` (missing keys are a no-op)."""
        ...

    def url(self, key: str) -> str:
        """Public URL for a key (empty when storage has no public base)."""
        ...


class LocalStorageService:
    """Filesystem-backed storage under ``base_dir``."""

    def __init__(self, base_dir: Path) -> None:
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def save(self, data: bytes, content_type: str, user_id: int, subdir: str = "") -> str:
        ext = _EXTENSIONS.get((content_type or "").split(";")[0].strip().lower(), "bin")
        folder = self.base_dir / str(user_id) / subdir
        folder.mkdir(parents=True, exist_ok=True)
        name = f"{secrets.token_hex(16)}.{ext}"
        key = f"{user_id}/{subdir}/{name}" if subdir else f"{user_id}/{name}"
        target = self.base_dir / key
        target.write_bytes(data)
        logger.debug("storage_saved", key=key, bytes=len(data))
        return key

    def delete(self, key: str) -> None:
        path = self.base_dir / key
        try:
            path.unlink(missing_ok=True)
        except OSError as exc:  # pragma: no cover - platform edge case
            logger.warning("storage_delete_failed", key=key, error=str(exc))

    def url(self, key: str) -> str:
        return f"/media/{key}"


def get_storage_service() -> StorageService:
    """Compose the configured storage provider (local today; S3 in M11)."""
    settings = get_settings()
    if settings.storage_provider == "s3":
        # M11: S3StorageService backed by boto3 + settings.s3_*. Until then a
        # clear error beats silently storing on disk behind a misconfigured key.
        raise NotImplementedError(
            "S3 storage provider is not wired yet; keep storage_provider=local"
        )
    return LocalStorageService(Path(settings.storage_local_dir))
