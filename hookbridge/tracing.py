"""Request tracing — attaches a unique trace ID to each webhook event
and propagates it through the pipeline for correlation."""
from __future__ import annotations

import uuid
import time
from dataclasses import dataclass, field
from typing import Dict, Optional, List


@dataclass
class Span:
    """A single timed operation within a trace."""
    name: str
    trace_id: str
    started_at: float = field(default_factory=time.monotonic)
    ended_at: Optional[float] = None
    tags: Dict[str, str] = field(default_factory=dict)

    def finish(self) -> None:
        self.ended_at = time.monotonic()

    @property
    def duration_ms(self) -> Optional[float]:
        if self.ended_at is None:
            return None
        return (self.ended_at - self.started_at) * 1000.0


@dataclass
class Trace:
    """Collection of spans sharing the same trace ID."""
    trace_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    spans: List[Span] = field(default_factory=list)

    def start_span(self, name: str, **tags: str) -> Span:
        span = Span(name=name, trace_id=self.trace_id, tags=dict(tags))
        self.spans.append(span)
        return span

    def as_dict(self) -> dict:
        return {
            "trace_id": self.trace_id,
            "spans": [
                {
                    "name": s.name,
                    "duration_ms": s.duration_ms,
                    "tags": s.tags,
                }
                for s in self.spans
            ],
        }


class TraceContext:
    """Thread-local-style registry mapping trace_id -> Trace."""

    def __init__(self) -> None:
        self._traces: Dict[str, Trace] = {}

    def new_trace(self) -> Trace:
        t = Trace()
        self._traces[t.trace_id] = t
        return t

    def get(self, trace_id: str) -> Optional[Trace]:
        return self._traces.get(trace_id)

    def remove(self, trace_id: str) -> None:
        self._traces.pop(trace_id, None)

    def all_traces(self) -> List[Trace]:
        return list(self._traces.values())
