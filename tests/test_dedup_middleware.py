"""Tests for hookbridge.dedup_middleware."""

import io
import json

import pytest

from hookbridge.dedup_middleware import DedupMiddleware
from hookbridge.throttle import ThrottleConfig, ThrottleStore


def _make_environ(path: str, payload: dict) -> dict:
    body = json.dumps(payload).encode()
    return {
        "PATH_INFO": path,
        "CONTENT_LENGTH": str(len(body)),
        "wsgi.input": io.BytesIO(body),
    }


def _passthrough_app(environ, start_response):
    start_response("200 OK", [("Content-Type", "application/json")])
    return [b'{"ok": true}']


@pytest.fixture()
def store() -> ThrottleStore:
    return ThrottleStore()


@pytest.fixture()
def middleware(store) -> DedupMiddleware:
    return DedupMiddleware(_passthrough_app, store=store)


PAYLOAD = {"event": "ping"}


def _call(mw, path, payload):
    responses = []

    def start_response(status, headers):
        responses.append((status, headers))

    body = b"".join(mw(_make_environ(path, payload), start_response))
    return responses[0][0], json.loads(body)


def test_first_request_passes_through(middleware):
    status, body = _call(middleware, "/hook/a", PAYLOAD)
    assert status == "200 OK"
    assert body == {"ok": True}


def test_duplicate_returns_409(middleware):
    _call(middleware, "/hook/a", PAYLOAD)
    status, body = _call(middleware, "/hook/a", PAYLOAD)
    assert status == "409 Conflict"
    assert body["error"] == "duplicate"
    assert body["seen"] == 2


def test_different_routes_not_deduplicated(middleware):
    _call(middleware, "/hook/a", PAYLOAD)
    status, _ = _call(middleware, "/hook/b", PAYLOAD)
    assert status == "200 OK"


def test_different_payloads_not_deduplicated(middleware):
    _call(middleware, "/hook/a", PAYLOAD)
    status, _ = _call(middleware, "/hook/a", {"event": "push"})
    assert status == "200 OK"


def test_disabled_throttle_never_rejects(store, middleware):
    store.configure("hook/a", ThrottleConfig(enabled=False))
    _call(middleware, "/hook/a", PAYLOAD)
    status, _ = _call(middleware, "/hook/a", PAYLOAD)
    assert status == "200 OK"


def test_body_forwarded_to_downstream():
    received = {}

    def capturing_app(environ, start_response):
        length = int(environ.get("CONTENT_LENGTH", 0))
        body = environ["wsgi.input"].read(length)
        received["body"] = json.loads(body)
        start_response("200 OK", [])
        return [b"{}"]

    mw = DedupMiddleware(capturing_app)
    payload = {"x": 42}
    env = _make_environ("/hook/z", payload)
    list(mw(env, lambda s, h: None))
    assert received["body"] == payload
