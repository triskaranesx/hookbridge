"""Payload snapshot store — captures and diffs incoming webhook payloads."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _fingerprint(payload: Dict[str, Any]) -> str:
    """Return a stable SHA-256 hex digest of a JSON-serialised payload."""
    serialised = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(serialised.encode()).hexdigest()


@dataclass
class Snapshot:
    route: str
    payload: Dict[str, Any]
    fingerprint: str
    captured_at: datetime = field(default_factory=_utc_now)
    event_id: Optional[str] = None


@dataclass
class DiffResult:
    added: Dict[str, Any]
    removed: Dict[str, Any]
    changed: Dict[str, Any]  # key -> (old_value, new_value)

    @property
    def has_changes(self) -> bool:
        return bool(self.added or self.removed or self.changed)


def _flat_diff(old: Dict[str, Any], new: Dict[str, Any]) -> DiffResult:
    """Shallow diff between two dicts."""
    added = {k: v for k, v in new.items() if k not in old}
    removed = {k: v for k, v in old.items() if k not in new}
    changed = {
        k: (old[k], new[k])
        for k in old.keys() & new.keys()
        if old[k] != new[k]
    }
    return DiffResult(added=added, removed=removed, changed=changed)


class SnapshotStore:
    """Keeps the latest snapshot per route and a bounded history."""

    def __init__(self, history_limit: int = 50) -> None:
        self._history_limit = history_limit
        self._latest: Dict[str, Snapshot] = {}
        self._history: Dict[str, List[Snapshot]] = {}

    def record(self, route: str, payload: Dict[str, Any], event_id: Optional[str] = None) -> Snapshot:
        snap = Snapshot(
            route=route,
            payload=payload,
            fingerprint=_fingerprint(payload),
            event_id=event_id,
        )
        previous = self._latest.get(route)
        if previous is None or previous.fingerprint != snap.fingerprint:
            history = self._history.setdefault(route, [])
            history.append(snap)
            if len(history) > self._history_limit:
                history.pop(0)
            self._latest[route] = snap
        return snap

    def latest(self, route: str) -> Optional[Snapshot]:
        return self._latest.get(route)

    def history(self, route: str) -> List[Snapshot]:
        return list(self._history.get(route, []))

    def diff(self, route: str, payload: Dict[str, Any]) -> Optional[DiffResult]:
        """Diff *payload* against the latest stored snapshot for *route*."""
        snap = self._latest.get(route)
        if snap is None:
            return None
        return _flat_diff(snap.payload, payload)

    def clear(self, route: Optional[str] = None) -> None:
        if route is None:
            self._latest.clear()
            self._history.clear()
        else:
            self._latest.pop(route, None)
            self._history.pop(route, None)
