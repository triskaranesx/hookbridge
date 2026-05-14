"""Rate limiting for webhook dispatch per route."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from threading import Lock
from typing import Dict, Optional


@dataclass
class RateLimitConfig:
    """Configuration for a token-bucket rate limiter."""
    max_tokens: int = 10          # burst capacity
    refill_rate: float = 1.0      # tokens added per second
    enabled: bool = True


@dataclass
class _Bucket:
    tokens: float
    last_refill: float = field(default_factory=time.monotonic)
    lock: Lock = field(default_factory=Lock, compare=False, repr=False)


class RateLimiter:
    """Per-route token-bucket rate limiter."""

    def __init__(self) -> None:
        self._configs: Dict[str, RateLimitConfig] = {}
        self._buckets: Dict[str, _Bucket] = {}

    def configure(self, route_name: str, config: RateLimitConfig) -> None:
        """Attach a rate-limit config to a named route."""
        self._configs[route_name] = config

    def _get_bucket(self, route_name: str, config: RateLimitConfig) -> _Bucket:
        if route_name not in self._buckets:
            self._buckets[route_name] = _Bucket(tokens=float(config.max_tokens))
        return self._buckets[route_name]

    def _refill(self, bucket: _Bucket, config: RateLimitConfig) -> None:
        now = time.monotonic()
        elapsed = now - bucket.last_refill
        added = elapsed * config.refill_rate
        bucket.tokens = min(config.max_tokens, bucket.tokens + added)
        bucket.last_refill = now

    def allow(self, route_name: str) -> bool:
        """Return True if the request is within the rate limit, False otherwise."""
        config = self._configs.get(route_name)
        if config is None or not config.enabled:
            return True

        bucket = self._get_bucket(route_name, config)
        with bucket.lock:
            self._refill(bucket, config)
            if bucket.tokens >= 1.0:
                bucket.tokens -= 1.0
                return True
            return False

    def remaining(self, route_name: str) -> Optional[float]:
        """Return current token count for a route, or None if unconfigured."""
        config = self._configs.get(route_name)
        if config is None:
            return None
        bucket = self._get_bucket(route_name, config)
        with bucket.lock:
            self._refill(bucket, config)
            return bucket.tokens

    def reset(self, route_name: str) -> None:
        """Reset the bucket for a route to full capacity."""
        if route_name in self._buckets:
            del self._buckets[route_name]
