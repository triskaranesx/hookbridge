"""Replay stored webhook events to a target URL."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from hookbridge.delivery import DeliveryResult, deliver
from hookbridge.retry import RetryPolicy


@dataclass
class ReplayEvent:
    """A recorded webhook event available for replay."""

    event_id: str
    route_name: str
    payload: Dict[str, Any]
    recorded_at: float = field(default_factory=time.time)
    headers: Dict[str, str] = field(default_factory=dict)


@dataclass
class ReplayStore:
    """In-memory store for recorded events."""

    _events: List[ReplayEvent] = field(default_factory=list)

    def record(self, event: ReplayEvent) -> None:
        """Add an event to the store."""
        self._events.append(event)

    def get_by_route(self, route_name: str) -> List[ReplayEvent]:
        """Return all events recorded for a given route."""
        return [e for e in self._events if e.route_name == route_name]

    def get_by_id(self, event_id: str) -> Optional[ReplayEvent]:
        """Return a single event by its ID, or None."""
        for event in self._events:
            if event.event_id == event_id:
                return event
        return None

    def all(self) -> List[ReplayEvent]:
        """Return all stored events."""
        return list(self._events)

    def clear(self) -> None:
        """Remove all stored events."""
        self._events.clear()


def replay_event(
    event: ReplayEvent,
    target_url: str,
    policy: Optional[RetryPolicy] = None,
) -> DeliveryResult:
    """Replay a single event to *target_url* using the given retry policy."""
    if policy is None:
        policy = RetryPolicy()
    return deliver(target_url, event.payload, policy, extra_headers=event.headers)


def replay_route(
    store: ReplayStore,
    route_name: str,
    target_url: str,
    policy: Optional[RetryPolicy] = None,
) -> List[DeliveryResult]:
    """Replay all recorded events for *route_name* to *target_url*."""
    results: List[DeliveryResult] = []
    for event in store.get_by_route(route_name):
        result = replay_event(event, target_url, policy)
        results.append(result)
    return results
