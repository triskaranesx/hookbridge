"""WSGI middleware that creates a Trace for every incoming request
and injects the trace_id into the environ for downstream handlers."""
from __future__ import annotations

from typing import Callable, Iterable

from hookbridge.tracing import TraceContext

TRACE_ID_HEADER = "X-HookBridge-Trace-Id"
ENVIRON_KEY = "hookbridge.trace_id"


class TracingMiddleware:
    """Wrap a WSGI app with automatic trace-ID injection."""

    def __init__(self, app: Callable, context: TraceContext | None = None) -> None:
        self._app = app
        self._ctx = context or TraceContext()

    @property
    def context(self) -> TraceContext:
        return self._ctx

    def __call__(self, environ: dict, start_response: Callable) -> Iterable[bytes]:
        # Honour an upstream trace-id if provided, otherwise mint a new trace.
        upstream = environ.get("HTTP_X_HOOKBRIDGE_TRACE_ID")
        if upstream:
            trace = self._ctx.get(upstream)
            if trace is None:
                from hookbridge.tracing import Trace
                import uuid
                trace = Trace(trace_id=upstream)
                self._ctx._traces[upstream] = trace
        else:
            trace = self._ctx.new_trace()

        environ[ENVIRON_KEY] = trace.trace_id

        span = trace.start_span("request", method=environ.get("REQUEST_METHOD", ""),
                                path=environ.get("PATH_INFO", ""))

        def _start_response(status: str, headers: list, exc_info=None):
            span.finish()
            headers.append((TRACE_ID_HEADER, trace.trace_id))
            return start_response(status, headers, exc_info)

        return self._app(environ, _start_response)
