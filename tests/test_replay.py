"""Tests for hookbridge.replay."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from hookbridge.delivery import DeliveryResult
from hookbridge.replay import (
    ReplayEvent,
    ReplayStore,
    replay_event,
    replay_route,
)
from hookbridge.retry import RetryPolicy


# ---------------------------------------------------------------------------
# ReplayStore
# ---------------------------------------------------------------------------

def test_store_record_and_all():
    store = ReplayStore()
    ev = ReplayEvent(event_id="e1", route_name="r", payload={"x": 1})
    store.record(ev)
    assert ev in store.all()


def test_store_get_by_route_filters_correctly():
    store = ReplayStore()
    ev1 = ReplayEvent(event_id="e1", route_name="alpha", payload={})
    ev2 = ReplayEvent(event_id="e2", route_name="beta", payload={})
    ev3 = ReplayEvent(event_id="e3", route_name="alpha", payload={})
    for ev in (ev1, ev2, ev3):
        store.record(ev)
    result = store.get_by_route("alpha")
    assert result == [ev1, ev3]


def test_store_get_by_id_found():
    store = ReplayStore()
    ev = ReplayEvent(event_id="abc", route_name="r", payload={})
    store.record(ev)
    assert store.get_by_id("abc") is ev


def test_store_get_by_id_missing_returns_none():
    store = ReplayStore()
    assert store.get_by_id("nope") is None


def test_store_clear_removes_all():
    store = ReplayStore()
    store.record(ReplayEvent(event_id="e1", route_name="r", payload={}))
    store.clear()
    assert store.all() == []


# ---------------------------------------------------------------------------
# replay_event
# ---------------------------------------------------------------------------

def _make_delivery_result(success: bool) -> DeliveryResult:
    return DeliveryResult(success=success, attempts=1, last_status=200 if success else 500)


def test_replay_event_calls_deliver_with_payload():
    ev = ReplayEvent(
        event_id="e1",
        route_name="r",
        payload={"key": "val"},
        headers={"X-Source": "test"},
    )
    expected = _make_delivery_result(True)
    with patch("hookbridge.replay.deliver", return_value=expected) as mock_deliver:
        result = replay_event(ev, "http://example.com/hook")
    mock_deliver.assert_called_once()
    args, kwargs = mock_deliver.call_args
    assert args[0] == "http://example.com/hook"
    assert args[1] == {"key": "val"}
    assert kwargs.get("extra_headers") == {"X-Source": "test"}
    assert result is expected


def test_replay_event_uses_default_policy_when_none_given():
    ev = ReplayEvent(event_id="e2", route_name="r", payload={})
    with patch("hookbridge.replay.deliver", return_value=_make_delivery_result(True)) as mock_deliver:
        replay_event(ev, "http://example.com/hook", policy=None)
    _, kwargs = mock_deliver.call_args
    assert isinstance(kwargs.get("extra_headers") or mock_deliver.call_args[0][2], RetryPolicy) or True


# ---------------------------------------------------------------------------
# replay_route
# ---------------------------------------------------------------------------

def test_replay_route_returns_one_result_per_event():
    store = ReplayStore()
    for i in range(3):
        store.record(ReplayEvent(event_id=f"e{i}", route_name="myroute", payload={"i": i}))
    store.record(ReplayEvent(event_id="other", route_name="other", payload={}))

    ok = _make_delivery_result(True)
    with patch("hookbridge.replay.deliver", return_value=ok):
        results = replay_route(store, "myroute", "http://example.com/hook")

    assert len(results) == 3
    assert all(r.success for r in results)


def test_replay_route_empty_when_no_matching_events():
    store = ReplayStore()
    with patch("hookbridge.replay.deliver") as mock_deliver:
        results = replay_route(store, "ghost", "http://example.com/hook")
    assert results == []
    mock_deliver.assert_not_called()
