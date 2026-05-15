"""Payload throttling: deduplicate events within a time window."""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple


@dataclass
class ThrottleConfig:
    window_seconds: float = 5.0
    enabled: bool = True


@dataclass
class _Entry:
    fingerprint: str
    first_seen: float
    count: int = 1


class ThrottleStore:
    """Tracks recently seen payload fingerprints per route."""

    def __init__(self) -> None:
        self._buckets: Dict[str, Dict[str, _Entry]] = {}
        self._configs: Dict[str, ThrottleConfig] = {}

    def configure(self, route: str, config: ThrottleConfig) -> None:
        self._configs[route] = config

    def _fingerprint(self, payload: dict) -> str:
        serialised = json.dumps(payload, sort_keys=True, default=str)
        return hashlib.sha1(serialised.encode()).hexdigest()

    def _evict(self, route: str, window: float, now: float) -> None:
        bucket = self._buckets.get(route, {})
        self._buckets[route] = {
            fp: e for fp, e in bucket.items() if now - e.first_seen < window
        }

    def is_duplicate(self, route: str, payload: dict) -> Tuple[bool, int]:
        """Return (is_duplicate, seen_count). Registers the payload."""
        config = self._configs.get(route, ThrottleConfig())
        if not config.enabled:
            return False, 1

        now = time.monotonic()
        self._evict(route, config.window_seconds, now)

        fp = self._fingerprint(payload)
        bucket = self._buckets.setdefault(route, {})

        if fp in bucket:
            bucket[fp].count += 1
            return True, bucket[fp].count

        bucket[fp] = _Entry(fingerprint=fp, first_seen=now)
        return False, 1

    def seen_count(self, route: str, payload: dict) -> Optional[int]:
        """Return how many times this payload has been seen, or None."""
        fp = self._fingerprint(payload)
        entry = self._buckets.get(route, {}).get(fp)
        return entry.count if entry else None

    def clear(self, route: Optional[str] = None) -> None:
        if route is None:
            self._buckets.clear()
        else:
            self._buckets.pop(route, None)
