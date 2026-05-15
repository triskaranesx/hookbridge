"""Simple in-memory exporter that collects finished traces
and exposes them for inspection or forwarding to an external system."""
from __future__ import annotations

from collections import deque
from typing import Deque, List, Optional

from hookbridge.tracing import Trace, TraceContext


class TraceExporter:
    """Collects completed traces up to *capacity* entries (FIFO eviction)."""

    def __init__(self, context: TraceContext, capacity: int = 500) -> None:
        self._ctx = context
        self._capacity = capacity
        self._exported: Deque[dict] = deque(maxlen=capacity)

    def export(self, trace_id: str) -> Optional[dict]:
        """Serialise a trace to a dict, store it, and remove it from the context."""
        trace = self._ctx.get(trace_id)
        if trace is None:
            return None
        snapshot = trace.as_dict()
        self._exported.append(snapshot)
        self._ctx.remove(trace_id)
        return snapshot

    def export_all(self) -> List[dict]:
        """Export every trace currently held in the context."""
        ids = [t.trace_id for t in self._ctx.all_traces()]
        results = []
        for tid in ids:
            result = self.export(tid)
            if result is not None:
                results.append(result)
        return results

    def collected(self) -> List[dict]:
        """Return all previously exported trace snapshots."""
        return list(self._exported)

    def clear(self) -> None:
        """Discard all stored snapshots."""
        self._exported.clear()

    @property
    def capacity(self) -> int:
        return self._capacity
