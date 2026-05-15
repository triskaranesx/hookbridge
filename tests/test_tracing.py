"""Unit tests for hookbridge.tracing."""
import time
import pytest
from hookbridge.tracing import Span, Trace, TraceContext


def test_span_duration_none_before_finish():
    s = Span(name="op", trace_id="abc")
    assert s.duration_ms is None


def test_span_duration_positive_after_finish():
    s = Span(name="op", trace_id="abc")
    time.sleep(0.01)
    s.finish()
    assert s.duration_ms is not None
    assert s.duration_ms > 0


def test_trace_generates_unique_ids():
    t1 = Trace()
    t2 = Trace()
    assert t1.trace_id != t2.trace_id


def test_trace_start_span_appends():
    t = Trace()
    s = t.start_span("step", route="demo")
    assert len(t.spans) == 1
    assert s.name == "step"
    assert s.tags == {"route": "demo"}


def test_trace_as_dict_structure():
    t = Trace(trace_id="fixed")
    s = t.start_span("work")
    s.finish()
    d = t.as_dict()
    assert d["trace_id"] == "fixed"
    assert len(d["spans"]) == 1
    assert "duration_ms" in d["spans"][0]


def test_context_new_trace_is_stored():
    ctx = TraceContext()
    t = ctx.new_trace()
    assert ctx.get(t.trace_id) is t


def test_context_remove_deletes_trace():
    ctx = TraceContext()
    t = ctx.new_trace()
    ctx.remove(t.trace_id)
    assert ctx.get(t.trace_id) is None


def test_context_all_traces_returns_list():
    ctx = TraceContext()
    ctx.new_trace()
    ctx.new_trace()
    assert len(ctx.all_traces()) == 2


def test_context_get_unknown_returns_none():
    ctx = TraceContext()
    assert ctx.get("nonexistent") is None
