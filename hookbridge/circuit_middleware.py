"""WSGI middleware that enforces circuit breaker state before forwarding requests."""

from __future__ import annotations

import json
from typing import Callable, Iterable

from hookbridge.circuit_breaker import CircuitBreaker

_CIRCUIT_OPEN_BODY = json.dumps({"error": "circuit open", "retryable": True}).encode()
_CONTENT_TYPE = [("Content-Type", "application/json")]


class CircuitBreakerMiddleware:
    """Wrap a WSGI app; return 503 for routes whose circuit is open."""

    def __init__(self, app: Callable, breaker: CircuitBreaker) -> None:
        self._app = app
        self._breaker = breaker

    def __call__(self, environ: dict, start_response: Callable) -> Iterable[bytes]:
        route = self._route_from_environ(environ)
        if route and self._breaker.is_open(route):
            start_response(
                "503 Service Unavailable",
                _CONTENT_TYPE + [("X-Circuit-State", "open")],
            )
            return [_CIRCUIT_OPEN_BODY]
        return self._app(environ, start_response)

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _route_from_environ(environ: dict) -> str | None:
        """Extract route name from X-Hookbridge-Route header or PATH_INFO."""
        header = environ.get("HTTP_X_HOOKBRIDGE_ROUTE")
        if header:
            return header
        path = environ.get("PATH_INFO", "")
        parts = [p for p in path.split("/") if p]
        # Expect /hook/<route> pattern
        if len(parts) >= 2 and parts[0] == "hook":
            return parts[1]
        return None
