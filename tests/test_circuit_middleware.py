"""Tests for hookbridge.circuit_middleware."""

import json
import pytest

from hookbridge.circuit_breaker import CircuitBreaker, CircuitBreakerConfig
from hookbridge.circuit_middleware import CircuitBreakerMiddleware


def _make_environ(path: str = "/hook/my_route", route_header: str | None = None) -> dict:
    env = {"PATH_INFO": path, "REQUEST_METHOD": "POST"}
    if route_header:
        env["HTTP_X_HOOKBRIDGE_ROUTE"] = route_header
    return env


def _passthrough_app(environ, start_response):
    start_response("200 OK", [("Content-Type", "application/json")])
    return [b'{"ok": true}']


def _call(middleware, environ):
    responses = []

    def start_response(status, headers):
        responses.append((status, dict(headers)))

    body = b"".join(middleware(environ, start_response))
    return responses[0][0], responses[0][1], body


@pytest.fixture
def breaker():
    cb = CircuitBreaker()
    cb.configure("my_route", CircuitBreakerConfig(failure_threshold=2, recovery_timeout=60.0))
    return cb


@pytest.fixture
def middleware(breaker):
    return CircuitBreakerMiddleware(_passthrough_app, breaker)


def test_closed_circuit_passes_through(middleware):
    status, _, body = _call(middleware, _make_environ())
    assert status == "200 OK"
    assert json.loads(body) == {"ok": True}


def test_open_circuit_returns_503(middleware, breaker):
    for _ in range(2):
        breaker.record_failure("my_route")
    status, headers, body = _call(middleware, _make_environ())
    assert status == "503 Service Unavailable"
    assert headers["X-Circuit-State"] == "open"
    assert json.loads(body)["retryable"] is True


def test_route_extracted_from_header(middleware, breaker):
    for _ in range(2):
        breaker.record_failure("my_route")
    env = _make_environ(path="/other", route_header="my_route")
    status, _, _ = _call(middleware, env)
    assert status == "503 Service Unavailable"


def test_unknown_route_passes_through(middleware):
    env = _make_environ(path="/hook/unknown_route")
    status, _, _ = _call(middleware, env)
    assert status == "200 OK"


def test_no_route_in_path_passes_through(middleware):
    env = _make_environ(path="/healthz")
    status, _, _ = _call(middleware, env)
    assert status == "200 OK"


def test_reset_allows_requests_again(middleware, breaker):
    for _ in range(2):
        breaker.record_failure("my_route")
    breaker.reset("my_route")
    status, _, _ = _call(middleware, _make_environ())
    assert status == "200 OK"
