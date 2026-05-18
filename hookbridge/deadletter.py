"""Dead-letter queue for failed webhook deliveries."""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class DeadLetterEntry:
    id: str
    route: str
    payload: Dict[str, Any]
    reason: str
    attempts: int
    failed_at: float
    tags: Dict[str, str] = field(default_factory=dict)


class DeadLetterQueue:
    """In-memory dead-letter queue with capacity eviction."""

    def __init__(self, capacity: int = 500) -> None:
        if capacity < 1:
            raise ValueError("capacity must be >= 1")
        self._capacity = capacity
        self._entries: List[DeadLetterEntry] = []

    # ------------------------------------------------------------------
    def record(
        self,
        route: str,
        payload: Dict[str, Any],
        reason: str,
        attempts: int,
        tags: Optional[Dict[str, str]] = None,
    ) -> DeadLetterEntry:
        entry = DeadLetterEntry(
            id=str(uuid.uuid4()),
            route=route,
            payload=payload,
            reason=reason,
            attempts=attempts,
            failed_at=time.time(),
            tags=tags or {},
        )
        if len(self._entries) >= self._capacity:
            self._entries.pop(0)
        self._entries.append(entry)
        return entry

    def all(self) -> List[DeadLetterEntry]:
        return list(self._entries)

    def get_by_route(self, route: str) -> List[DeadLetterEntry]:
        return [e for e in self._entries if e.route == route]

    def get_by_id(self, entry_id: str) -> Optional[DeadLetterEntry]:
        for e in self._entries:
            if e.id == entry_id:
                return e
        return None

    def remove(self, entry_id: str) -> bool:
        """Remove an entry by id. Returns True if removed."""
        for i, e in enumerate(self._entries):
            if e.id == entry_id:
                self._entries.pop(i)
                return True
        return False

    def clear(self) -> None:
        self._entries.clear()

    def __len__(self) -> int:
        return len(self._entries)
