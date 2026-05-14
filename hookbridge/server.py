"""Minimal WSGI-compatible HTTP server entry-point for hookbridge.

Exposes two endpoints:
  POST /hooks/<route>   — receive an incoming webhook payload
  GET  /health          — return a JSON health report
"""

from __future__ import annotations

import json
from typing import Callable, Iterable

from hookbridge.health import build_report, report_as_dict
from hookbridge.metrics import MetricsStore
from hookbridge.router import Router


WSGIEnviron = dict
StartResponse = Callable


class HookBridgeApp:
    """Tiny WSGI application that wires together the router and health endpoint."""

    def __init__(self, router: Router, metrics: MetricsStore) -> None:
        self._router = router
        self._metrics = metrics

    # ------------------------------------------------------------------
    # WSGI interface
    # ------------------------------------------------------------------

    def __call__(self, environ: WSGIEnviron, start_response: StartResponse) -> Iterable[bytes]:
        method = environ.get("REQUEST_METHOD", "GET").upper()
        path = environ.get("PATH_INFO", "/")

        if method == "GET" and path == "/health":
            return self._handle_health(start_response)

        if method == "POST" and path.startswith("/hooks/"):
            route_name = path[len("/hooks/"):].strip("/")
            return self._handle_hook(environ, start_response, route_name)

        return self._respond(start_response, 404, {"error": "not found"})

    # ------------------------------------------------------------------
    # handlers
    # ------------------------------------------------------------------

    def _handle_health(self, start_response: StartResponse) -> Iterable[bytes]:
        report = build_report(self._metrics)
        status_code = 200 if report.healthy else 503
        return self._respond(start_response, status_code, report_as_dict(report))

    def _handle_hook(
        self,
        environ: WSGIEnviron,
        start_response: StartResponse,
        route_name: str,
    ) -> Iterable[bytes]:
        try:
            length = int(environ.get("CONTENT_LENGTH") or 0)
            raw = environ["wsgi.input"].read(length)
            payload: dict = json.loads(raw) if raw else {}
        except (ValueError, KeyError):
            return self._respond(start_response, 400, {"error": "invalid JSON"})

        dispatched = self._router.dispatch(route_name, payload)
        if not dispatched:
            return self._respond(start_response, 404, {"error": "no matching route"})

        return self._respond(start_response, 202, {"status": "accepted", "routes": dispatched})

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _respond(
        start_response: StartResponse,
        status_code: int,
        body: dict,
    ) -> Iterable[bytes]:
        encoded = json.dumps(body).encode()
        reason = {200: "OK", 202: "Accepted", 400: "Bad Request", 404: "Not Found", 503: "Service Unavailable"}.get(status_code, "")
        start_response(f"{status_code} {reason}", [
            ("Content-Type", "application/json"),
            ("Content-Length", str(len(encoded))),
        ])
        return [encoded]


def create_app(router: Router, metrics: MetricsStore) -> HookBridgeApp:
    """Factory used by the CLI or test fixtures."""
    return HookBridgeApp(router=router, metrics=metrics)
