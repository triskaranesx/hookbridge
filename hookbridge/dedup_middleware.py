"""WSGI-style middleware that drops duplicate webhook payloads."""

from __future__ import annotations

import io
import json
import logging
from typing import Callable, Optional

from hookbridge.throttle import ThrottleStore

logger = logging.getLogger(__name__)

_START_RESPONSE = Callable  # (status, headers) -> None
_APP = Callable  # WSGI app


class DedupMiddleware:
    """Wraps a WSGI application and rejects duplicate payloads.

    A 409 Conflict is returned when a payload fingerprint has already been
    seen for the same route within the configured window.
    """

    def __init__(self, app: _APP, store: Optional[ThrottleStore] = None) -> None:
        self._app = app
        self._store = store or ThrottleStore()

    @property
    def store(self) -> ThrottleStore:
        return self._store

    def _route_from_environ(self, environ: dict) -> str:
        return environ.get("PATH_INFO", "/").strip("/") or "root"

    def _read_body(self, environ: dict) -> bytes:
        try:
            length = int(environ.get("CONTENT_LENGTH") or 0)
        except ValueError:
            length = 0
        return environ["wsgi.input"].read(length) if length else b""

    def _restore_body(self, environ: dict, body: bytes) -> None:
        """Rewind the request body so downstream apps can read it normally."""
        environ["wsgi.input"] = io.BytesIO(body)
        environ["CONTENT_LENGTH"] = str(len(body))

    def __call__(self, environ: dict, start_response: _START_RESPONSE):
        body = self._read_body(environ)

        try:
            payload = json.loads(body) if body else {}
        except (json.JSONDecodeError, ValueError):
            payload = {"_raw": body.decode(errors="replace")}

        route = self._route_from_environ(environ)
        is_dup, count = self._store.is_duplicate(route, payload)

        if is_dup:
            logger.debug("Duplicate payload on route %r (seen %d times)", route, count)
            start_response(
                "409 Conflict",
                [("Content-Type", "application/json")],
            )
            resp = json.dumps({"error": "duplicate", "seen": count}).encode()
            return [resp]

        # Restore body for downstream app
        self._restore_body(environ, body)
        return self._app(environ, start_response)
