"""CORS middleware for HookBridge — adds Cross-Origin Resource Sharing headers
to responses, with per-route or global configuration."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Iterable, Optional


@dataclass
class CORSConfig:
    """Configuration for CORS header injection."""

    allow_origins: list[str] = field(default_factory=lambda: ["*"])
    allow_methods: list[str] = field(
        default_factory=lambda: ["GET", "POST", "OPTIONS"]
    )
    allow_headers: list[str] = field(
        default_factory=lambda: ["Content-Type", "X-Hub-Signature-256"]
    )
    expose_headers: list[str] = field(default_factory=list)
    allow_credentials: bool = False
    max_age: Optional[int] = 600  # seconds


def _origin_allowed(origin: str, allowed: list[str]) -> bool:
    """Return True if *origin* is covered by the *allowed* list."""
    if "*" in allowed:
        return True
    return origin in allowed


def _build_headers(config: CORSConfig, request_origin: str) -> list[tuple[str, str]]:
    """Build the CORS response headers for a given request origin."""
    if not _origin_allowed(request_origin, config.allow_origins):
        return []

    origin_value = "*" if "*" in config.allow_origins else request_origin
    headers: list[tuple[str, str]] = [
        ("Access-Control-Allow-Origin", origin_value),
        ("Access-Control-Allow-Methods", ", ".join(config.allow_methods)),
        ("Access-Control-Allow-Headers", ", ".join(config.allow_headers)),
    ]
    if config.expose_headers:
        headers.append(
            ("Access-Control-Expose-Headers", ", ".join(config.expose_headers))
        )
    if config.allow_credentials:
        headers.append(("Access-Control-Allow-Credentials", "true"))
    if config.max_age is not None:
        headers.append(("Access-Control-Max-Age", str(config.max_age)))
    return headers


class CORSMiddleware:
    """WSGI middleware that injects CORS headers and handles preflight requests."""

    def __init__(self, app: Callable, config: Optional[CORSConfig] = None) -> None:
        self._app = app
        self._config = config or CORSConfig()

    def __call__(
        self,
        environ: dict,
        start_response: Callable,
    ) -> Iterable[bytes]:
        origin = environ.get("HTTP_ORIGIN", "")
        method = environ.get("REQUEST_METHOD", "")

        cors_headers = _build_headers(self._config, origin) if origin else []

        # Handle preflight
        if method == "OPTIONS" and origin:
            start_response("204 No Content", cors_headers)
            return [b""]

        def _start_response_with_cors(status: str, headers: list, exc_info=None):
            combined = list(headers) + cors_headers
            return start_response(status, combined, exc_info)

        return self._app(environ, _start_response_with_cors)
