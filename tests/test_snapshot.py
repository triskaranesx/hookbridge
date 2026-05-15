"""Tests for hookbridge.snapshot."""

import pytest
from hookbridge.snapshot import SnapshotStore, _fingerprint, _flat_diff


# ---------------------------------------------------------------------------
# _fingerprint
# ---------------------------------------------------------------------------

def test_fingerprint_is_deterministic():
    p = {"b": 2, "a": 1}
    assert _fingerprint(p) == _fingerprint(p)


def test_fingerprint_key_order_independent():
    assert _fingerprint({"a": 1, "b": 2}) == _fingerprint({"b": 2, "a": 1})


def test_fingerprint_differs_for_different_payloads():
    assert _fingerprint({"a": 1}) != _fingerprint({"a": 2})


# ---------------------------------------------------------------------------
# _flat_diff
# ---------------------------------------------------------------------------

def test_flat_diff_added():
    result = _flat_diff({"a": 1}, {"a": 1, "b": 2})
    assert result.added == {"b": 2}
    assert not result.removed
    assert not result.changed


def test_flat_diff_removed():
    result = _flat_diff({"a": 1, "b": 2}, {"a": 1})
    assert result.removed == {"b": 2}
    assert not result.added


def test_flat_diff_changed():
    result = _flat_diff({"a": 1}, {"a": 99})
    assert result.changed == {"a": (1, 99)}


def test_flat_diff_no_changes_has_changes_false():
    result = _flat_diff({"a": 1}, {"a": 1})
    assert not result.has_changes


# ---------------------------------------------------------------------------
# SnapshotStore.record
# ---------------------------------------------------------------------------

def test_record_returns_snapshot():
    store = SnapshotStore()
    snap = store.record("route-a", {"x": 1})
    assert snap.route == "route-a"
    assert snap.fingerprint == _fingerprint({"x": 1})


def test_record_stores_latest():
    store = SnapshotStore()
    store.record("route-a", {"x": 1})
    assert store.latest("route-a") is not None


def test_record_duplicate_payload_not_added_to_history():
    store = SnapshotStore()
    store.record("route-a", {"x": 1})
    store.record("route-a", {"x": 1})  # identical — should not append
    assert len(store.history("route-a")) == 1


def test_record_different_payload_appends_history():
    store = SnapshotStore()
    store.record("route-a", {"x": 1})
    store.record("route-a", {"x": 2})
    assert len(store.history("route-a")) == 2


def test_record_respects_history_limit():
    store = SnapshotStore(history_limit=3)
    for i in range(5):
        store.record("r", {"i": i})
    assert len(store.history("r")) == 3


def test_record_event_id_stored():
    store = SnapshotStore()
    snap = store.record("r", {"k": "v"}, event_id="evt-123")
    assert snap.event_id == "evt-123"


# ---------------------------------------------------------------------------
# SnapshotStore.diff
# ---------------------------------------------------------------------------

def test_diff_returns_none_when_no_snapshot():
    store = SnapshotStore()
    assert store.diff("unknown", {"a": 1}) is None


def test_diff_detects_changes():
    store = SnapshotStore()
    store.record("r", {"a": 1})
    result = store.diff("r", {"a": 2})
    assert result is not None
    assert result.has_changes


# ---------------------------------------------------------------------------
# SnapshotStore.clear
# ---------------------------------------------------------------------------

def test_clear_specific_route():
    store = SnapshotStore()
    store.record("r1", {"a": 1})
    store.record("r2", {"b": 2})
    store.clear("r1")
    assert store.latest("r1") is None
    assert store.latest("r2") is not None


def test_clear_all_routes():
    store = SnapshotStore()
    store.record("r1", {"a": 1})
    store.record("r2", {"b": 2})
    store.clear()
    assert store.latest("r1") is None
    assert store.latest("r2") is None
