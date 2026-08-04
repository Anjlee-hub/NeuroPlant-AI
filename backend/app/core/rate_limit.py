"""Lightweight in-process rate limiting (config-gated).

Redis-backed limits arrive in M11 hardening. Until then a small token bucket
per key keeps scan uploads (and anything else we annotate) bounded in
production where ``rate_limit_enabled=True``, while native dev and tests stay
unrestricted. The limiter is a no-op when disabled, so this module never blocks
a default local run.

The bucket refills continuously rather than resetting per minute, which is
friendlier to bursty phone-upload patterns: a user gets a full minute's budget
back in under a minute after a burst.
"""

from __future__ import annotations

import time
from typing import Final

from app.core.config import get_settings

# Buckets idle longer than this are evicted when the table grows (memory bound).
_IDLE_EVICT_SECONDS: Final = 30 * 60
_MAX_BUCKETS: Final = 100_000


class TokenBucket:
    """Fixed-capacity, continuous-refill token bucket."""

    __slots__ = ("capacity", "refill_per_sec", "_tokens", "_updated")

    def __init__(self, capacity: float, refill_per_sec: float) -> None:
        self.capacity = capacity
        self.refill_per_sec = refill_per_sec
        self._tokens = capacity
        self._updated = time.monotonic()

    def consume(self) -> bool:
        """Take one token; returns False when the bucket is empty."""
        now = time.monotonic()
        refilled = min(self.capacity, self._tokens + (now - self._updated) * self.refill_per_sec)
        self._tokens = refilled
        self._updated = now
        if self._tokens >= 1.0:
            self._tokens -= 1.0
            return True
        return False


class RateLimiter:
    """Per-key token buckets with bounded memory (idle buckets are evicted)."""

    def __init__(
        self,
        *,
        capacity: float = 10.0,
        refill_per_sec: float = 10.0 / 60.0,
        enabled: bool = True,
        max_buckets: int = _MAX_BUCKETS,
    ) -> None:
        self.capacity = capacity
        self.refill_per_sec = refill_per_sec
        self.enabled = enabled
        self.max_buckets = max_buckets
        self._buckets: dict[str, TokenBucket] = {}

    def allow(self, key: str) -> bool:
        """True when the key may proceed; False when it is over quota."""
        if not self.enabled:
            return True
        if len(self._buckets) >= self.max_buckets:
            self._evict_idle()
        bucket = self._buckets.get(key)
        if bucket is None:
            bucket = TokenBucket(self.capacity, self.refill_per_sec)
            self._buckets[key] = bucket
        return bucket.consume()

    def _evict_idle(self) -> None:
        cutoff = time.monotonic() - _IDLE_EVICT_SECONDS
        stale = [k for k, b in self._buckets.items() if b._updated < cutoff]
        for key in stale:
            del self._buckets[key]


_scan_limiter: RateLimiter | None = None


def get_scan_limiter() -> RateLimiter:
    """Process-wide scan limiter, composed once from settings."""
    global _scan_limiter
    if _scan_limiter is None:
        settings = get_settings()
        _scan_limiter = RateLimiter(
            capacity=settings.rate_limit_scan_per_minute,
            refill_per_sec=settings.rate_limit_scan_per_minute / 60.0,
            enabled=settings.rate_limit_enabled,
        )
    return _scan_limiter
