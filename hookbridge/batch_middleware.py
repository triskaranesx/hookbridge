"""WSGI middleware that accumulates webhook payloads into batches per route."""

from __future__ import annotations

import json
from typing import Any, Callable, Dict, Iterable, List, Optional

from hookbridge.batch import BatchConfig, BatchStore


class BatchMiddleware:
    """Intercept incoming hook requests and buffer them in a BatchStore.

    When a batch is flushed (size threshold or manual flush), the combined
    payload list is forwarded to the wrapped application as a JSON array.
    """

    def __init__(
        self,
        app: Callable,
        store: Optional[BatchStore] = None,
        config: Optional[BatchConfig] = None,
    ) -> None:
        self._app = app
        self._store = store if store is not None else BatchStore(config)
        self._store.set_flush_hook(self._on_flush)
        self._pending_flush: Optional[Dict[str, Any]] = None

    @property
    def store(self) -> BatchStore:
        return self._store

    def __call__(self, environ: Dict[str, Any], start_response: Callable) -> Iterable[bytes]:
        route = self._route_from_environ(environ)
        payload = self._read_payload(environ)

        if payload is None:
            return self._app(environ, start_response)

        self._pending_flush = None
        self._store.add(route, payload)

        if self._pending_flush is not None:
            # Batch was flushed; forward combined payload to app.
            body = json.dumps(self._pending_flush["payloads"]).encode()
            new_environ = dict(environ)
            new_environ["wsgi.input"] = __import__("io").BytesIO(body)
            new_environ["CONTENT_LENGTH"] = str(len(body))
            new_environ["CONTENT_TYPE"] = "application/json"
            new_environ["HTTP_X_BATCH_SIZE"] = str(self._pending_flush["size"])
            return self._app(new_environ, start_response)

        # Batch not yet full — return 202 Accepted.
        start_response("202 Accepted", [("Content-Type", "application/json")])
        return [b'{"status": "batched"}']

    def _on_flush(self, route: str, payloads: List[Dict[str, Any]]) -> None:
        self._pending_flush = {"route": route, "payloads": payloads, "size": len(payloads)}

    @staticmethod
    def _route_from_environ(environ: Dict[str, Any]) -> str:
        path = environ.get("PATH_INFO", "/")
        parts = [p for p in path.strip("/").split("/") if p]
        return parts[0] if parts else "default"

    @staticmethod
    def _read_payload(environ: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        try:
            length = int(environ.get("CONTENT_LENGTH") or 0)
            if length <= 0:
                return None
            body = environ["wsgi.input"].read(length)
            return json.loads(body)
        except (ValueError, KeyError, json.JSONDecodeError):
            return None
