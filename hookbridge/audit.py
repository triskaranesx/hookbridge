"""Audit log for webhook dispatch events."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class AuditEntry:
    route: str
    event_id: str
    status: str  # 'dispatched' | 'filtered' | 'rate_limited' | 'failed'
    payload_size: int
    timestamp: float = field(default_factory=time.time)
    target_url: Optional[str] = None
    attempts: int = 0
    error: Optional[str] = None
    tags: Dict[str, str] = field(default_factory=dict)


class AuditLog:
    """In-memory audit log with bounded capacity."""

    def __init__(self, max_entries: int = 1000) -> None:
        self._max = max_entries
        self._entries: List[AuditEntry] = []

    def record(self, entry: AuditEntry) -> None:
        """Append *entry*, evicting the oldest record when at capacity."""
        if len(self._entries) >= self._max:
            self._entries.pop(0)
        self._entries.append(entry)

    def all(self) -> List[AuditEntry]:
        """Return a shallow copy of all entries, oldest first."""
        return list(self._entries)

    def by_route(self, route: str) -> List[AuditEntry]:
        """Return entries for a specific route."""
        return [e for e in self._entries if e.route == route]

    def by_status(self, status: str) -> List[AuditEntry]:
        """Return entries with a specific status."""
        return [e for e in self._entries if e.status == status]

    def since(self, timestamp: float) -> List[AuditEntry]:
        """Return entries recorded at or after *timestamp*."""
        return [e for e in self._entries if e.timestamp >= timestamp]

    def clear(self) -> None:
        """Remove all entries."""
        self._entries.clear()

    def __len__(self) -> int:
        return len(self._entries)


def make_entry(
    route: str,
    event_id: str,
    status: str,
    payload: Any,
    *,
    target_url: Optional[str] = None,
    attempts: int = 0,
    error: Optional[str] = None,
    tags: Optional[Dict[str, str]] = None,
) -> AuditEntry:
    """Convenience factory that computes *payload_size* automatically."""
    size = len(payload) if isinstance(payload, (bytes, str)) else 0
    return AuditEntry(
        route=route,
        event_id=event_id,
        status=status,
        payload_size=size,
        target_url=target_url,
        attempts=attempts,
        error=error,
        tags=tags or {},
    )
