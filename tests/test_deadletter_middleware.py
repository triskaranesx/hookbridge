"""Tests for hookbridge.deadletter_middleware."""
from typing import Any, Callable, Dict, Iterable
import pytest
from hookbridge.deadletter import DeadLetterQueue
from hookbridge.deadletter_middleware import DeadLetterMiddleware
from hookbridge.delivery import DeliveryResult


def _make_result(success: bool, attempts: int = 1, error: str = "") -> DeliveryResult:
    return DeliveryResult(success=success, status_code=500 if not success else 200,
                          attempts=attempts, error=error or None)


def _passthrough_app(environ: Dict[str, Any], start_response: Callable) -> Iterable[bytes]:
    start_response("200 OK", [])
    return [b"ok"]


def _call(middleware, environ):
    responses = []

    def start_response(status, headers):
        responses.append(status)

    list(middleware(environ, start_response))
    return responses


@pytest.fixture()
def queue() -> DeadLetterQueue:
    return DeadLetterQueue()


@pytest.fixture()
def middleware(queue) -> DeadLetterMiddleware:
    return DeadLetterMiddleware(_passthrough_app, queue=queue)


def test_successful_delivery_not_recorded(middleware, queue):
    environ = {"hookbridge.delivery_result": _make_result(True), "hookbridge.route": "r"}
    _call(middleware, environ)
    assert len(queue) == 0


def test_failed_delivery_is_recorded(middleware, queue):
    environ = {
        "hookbridge.delivery_result": _make_result(False, attempts=3, error="timeout"),
        "hookbridge.route": "my-route",
        "hookbridge.payload": {"event": "push"},
    }
    _call(middleware, environ)
    assert len(queue) == 1
    entry = queue.all()[0]
    assert entry.route == "my-route"
    assert entry.reason == "timeout"
    assert entry.attempts == 3
    assert entry.payload == {"event": "push"}


def test_no_delivery_result_is_ignored(middleware, queue):
    _call(middleware, {})
    assert len(queue) == 0


def test_unknown_route_defaults(middleware, queue):
    environ = {"hookbridge.delivery_result": _make_result(False)}
    _call(middleware, environ)
    assert queue.all()[0].route == "unknown"


def test_payload_read_from_body_json(middleware, queue):
    import json
    body = json.dumps({"k": "v"}).encode()
    environ = {
        "hookbridge.delivery_result": _make_result(False),
        "hookbridge.body": body,
    }
    _call(middleware, environ)
    assert queue.all()[0].payload == {"k": "v"}


def test_payload_invalid_json_stored_as_raw(middleware, queue):
    environ = {
        "hookbridge.delivery_result": _make_result(False),
        "hookbridge.body": b"not-json",
    }
    _call(middleware, environ)
    assert "_raw" in queue.all()[0].payload


def test_multiple_failures_accumulate(middleware, queue):
    for i in range(3):
        environ = {
            "hookbridge.delivery_result": _make_result(False),
            "hookbridge.route": f"route-{i}",
        }
        _call(middleware, environ)
    assert len(queue) == 3


def test_custom_queue_shared(queue):
    mw = DeadLetterMiddleware(_passthrough_app, queue=queue)
    environ = {"hookbridge.delivery_result": _make_result(False)}
    _call(mw, environ)
    assert mw.queue is queue
    assert len(queue) == 1
