"""Unit tests for hookbridge.tracing_middleware."""
import pytest
from hookbridge.tracing import TraceContext
from hookbridge.tracing_middleware import (
    TracingMiddleware,
    TRACE_ID_HEADER,
    ENVIRON_KEY,
)


def _make_environ(path: str = "/hook", method: str = "POST", extra: dict | None = None) -> dict:
    env = {"REQUEST_METHOD": method, "PATH_INFO": path}
    if extra:
        env.update(extra)
    return env


def _passthrough_app(environ, start_response):
    start_response("200 OK", [])
    return [b"ok"]


def _call(middleware, environ):
    captured = {}

    def start_response(status, headers, exc_info=None):
        captured["status"] = status
        captured["headers"] = dict(headers)

    body = list(middleware(environ, start_response))
    return captured, body


def test_trace_id_injected_into_environ():
    ctx = TraceContext()
    mw = TracingMiddleware(_passthrough_app, ctx)
    env = _make_environ()
    mw(env, lambda s, h, e=None: None)
    assert ENVIRON_KEY in env
    assert len(env[ENVIRON_KEY]) == 32  # uuid4 hex


def test_trace_id_header_in_response():
    ctx = TraceContext()
    mw = TracingMiddleware(_passthrough_app, ctx)
    env = _make_environ()
    captured, _ = _call(mw, env)
    assert TRACE_ID_HEADER in captured["headers"]


def test_upstream_trace_id_reused():
    ctx = TraceContext()
    mw = TracingMiddleware(_passthrough_app, ctx)
    env = _make_environ(extra={"HTTP_X_HOOKBRIDGE_TRACE_ID": "deadbeef" * 4})
    captured, _ = _call(mw, env)
    assert captured["headers"][TRACE_ID_HEADER] == "deadbeef" * 4


def test_span_is_recorded_in_trace():
    ctx = TraceContext()
    mw = TracingMiddleware(_passthrough_app, ctx)
    env = _make_environ()
    _call(mw, env)
    trace_id = env[ENVIRON_KEY]
    trace = ctx.get(trace_id)
    assert trace is not None
    assert len(trace.spans) == 1
    assert trace.spans[0].name == "request"


def test_span_finished_after_response():
    ctx = TraceContext()
    mw = TracingMiddleware(_passthrough_app, ctx)
    env = _make_environ()
    _call(mw, env)
    trace = ctx.get(env[ENVIRON_KEY])
    assert trace.spans[0].duration_ms is not None


def test_default_context_created_when_none_provided():
    mw = TracingMiddleware(_passthrough_app)
    assert isinstance(mw.context, TraceContext)
