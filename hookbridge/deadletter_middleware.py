"""WSGI middleware that captures failed deliveries into a DeadLetterQueue."""
from __future__ import annotations

import json
from typing import Any, Callable, Dict, Iterable, List, Optional

from hookbridge.deadletter import DeadLetterQueue
from hookbridge.delivery import DeliveryResult


class DeadLetterMiddleware:
    """Intercepts DeliveryResult objects stored in the environ and records
    failures in a shared DeadLetterQueue.

    Upstream WSGI apps should set ``hookbridge.delivery_result`` in the
    environ to a :class:`~hookbridge.delivery.DeliveryResult` instance so
    this middleware can inspect it.
    """

    ENVIRON_KEY = "hookbridge.delivery_result"
    ROUTE_KEY = "hookbridge.route"

    def __init__(
        self,
        app: Callable,
        queue: Optional[DeadLetterQueue] = None,
    ) -> None:
        self._app = app
        self._queue: DeadLetterQueue = queue or DeadLetterQueue()

    @property
    def queue(self) -> DeadLetterQueue:
        return self._queue

    def __call__(
        self,
        environ: Dict[str, Any],
        start_response: Callable,
    ) -> Iterable[bytes]:
        response = self._app(environ, start_response)

        result: Optional[DeliveryResult] = environ.get(self.ENVIRON_KEY)
        if result is not None and not result.success:
            route = environ.get(self.ROUTE_KEY, "unknown")
            payload = self._read_payload(environ)
            self._queue.record(
                route=route,
                payload=payload,
                reason=result.error or "delivery failed",
                attempts=result.attempts,
            )

        return response

    @staticmethod
    def _read_payload(environ: Dict[str, Any]) -> Dict[str, Any]:
        raw: Any = environ.get("hookbridge.payload")
        if isinstance(raw, dict):
            return raw
        body: bytes = environ.get("hookbridge.body", b"")
        if body:
            try:
                return json.loads(body)
            except (ValueError, TypeError):
                return {"_raw": body.decode(errors="replace")}
        return {}
