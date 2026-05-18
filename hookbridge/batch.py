"""Batch delivery: group multiple webhook events and flush as a single request."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional


@dataclass
class BatchConfig:
    max_size: int = 10
    max_wait_seconds: float = 5.0
    enabled: bool = True


@dataclass
class BatchEntry:
    route: str
    payload: Dict[str, Any]
    received_at: float = field(default_factory=time.monotonic)


@dataclass
class Batch:
    route: str
    entries: List[BatchEntry] = field(default_factory=list)
    created_at: float = field(default_factory=time.monotonic)

    def add(self, entry: BatchEntry) -> None:
        self.entries.append(entry)

    def size(self) -> int:
        return len(self.entries)

    def age_seconds(self) -> float:
        return time.monotonic() - self.created_at

    def payloads(self) -> List[Dict[str, Any]]:
        return [e.payload for e in self.entries]


class BatchStore:
    def __init__(self, config: Optional[BatchConfig] = None) -> None:
        self._config = config or BatchConfig()
        self._batches: Dict[str, Batch] = {}
        self._flush_hook: Optional[Callable[[str, List[Dict[str, Any]]], None]] = None

    def set_flush_hook(self, hook: Callable[[str, List[Dict[str, Any]]], None]) -> None:
        self._flush_hook = hook

    def add(self, route: str, payload: Dict[str, Any]) -> Optional[Batch]:
        """Add payload to the route's batch. Returns flushed Batch if threshold met."""
        if not self._config.enabled:
            return None
        if route not in self._batches:
            self._batches[route] = Batch(route=route)
        batch = self._batches[route]
        batch.add(BatchEntry(route=route, payload=payload))
        if self._should_flush(batch):
            return self._flush(route)
        return None

    def flush(self, route: str) -> Optional[Batch]:
        """Manually flush the batch for a given route."""
        if route not in self._batches or self._batches[route].size() == 0:
            return None
        return self._flush(route)

    def flush_stale(self) -> List[Batch]:
        """Flush all batches that have exceeded max_wait_seconds."""
        flushed = []
        for route in list(self._batches):
            batch = self._batches[route]
            if batch.size() > 0 and batch.age_seconds() >= self._config.max_wait_seconds:
                result = self._flush(route)
                if result:
                    flushed.append(result)
        return flushed

    def pending(self, route: str) -> int:
        """Return number of pending entries for a route."""
        return self._batches[route].size() if route in self._batches else 0

    def _should_flush(self, batch: Batch) -> bool:
        return batch.size() >= self._config.max_size

    def _flush(self, route: str) -> Batch:
        batch = self._batches.pop(route)
        if self._flush_hook:
            self._flush_hook(route, batch.payloads())
        return batch
