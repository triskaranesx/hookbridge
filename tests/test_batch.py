"""Tests for hookbridge.batch."""

import time
from unittest.mock import MagicMock

import pytest

from hookbridge.batch import Batch, BatchConfig, BatchEntry, BatchStore


@pytest.fixture()
def store() -> BatchStore:
    return BatchStore(BatchConfig(max_size=3, max_wait_seconds=2.0))


def test_add_below_threshold_returns_none(store: BatchStore) -> None:
    result = store.add("route-a", {"x": 1})
    assert result is None


def test_add_at_threshold_returns_batch(store: BatchStore) -> None:
    store.add("route-a", {"x": 1})
    store.add("route-a", {"x": 2})
    result = store.add("route-a", {"x": 3})
    assert result is not None
    assert result.size() == 3


def test_flushed_batch_contains_correct_payloads(store: BatchStore) -> None:
    store.add("route-a", {"n": 1})
    store.add("route-a", {"n": 2})
    batch = store.add("route-a", {"n": 3})
    assert batch is not None
    assert batch.payloads() == [{"n": 1}, {"n": 2}, {"n": 3}]


def test_pending_count_increments(store: BatchStore) -> None:
    store.add("route-b", {"a": 1})
    store.add("route-b", {"a": 2})
    assert store.pending("route-b") == 2


def test_pending_returns_zero_for_unknown_route(store: BatchStore) -> None:
    assert store.pending("unknown") == 0


def test_flush_clears_pending(store: BatchStore) -> None:
    store.add("route-c", {"v": 1})
    store.flush("route-c")
    assert store.pending("route-c") == 0


def test_flush_returns_none_when_empty(store: BatchStore) -> None:
    result = store.flush("route-empty")
    assert result is None


def test_flush_hook_called_on_threshold(store: BatchStore) -> None:
    hook = MagicMock()
    store.set_flush_hook(hook)
    store.add("route-d", {"i": 0})
    store.add("route-d", {"i": 1})
    store.add("route-d", {"i": 2})
    hook.assert_called_once_with("route-d", [{"i": 0}, {"i": 1}, {"i": 2}])


def test_flush_hook_called_on_manual_flush(store: BatchStore) -> None:
    hook = MagicMock()
    store.set_flush_hook(hook)
    store.add("route-e", {"k": "v"})
    store.flush("route-e")
    hook.assert_called_once()


def test_flush_stale_flushes_aged_batches() -> None:
    cfg = BatchConfig(max_size=100, max_wait_seconds=0.05)
    s = BatchStore(cfg)
    s.add("route-f", {"t": 1})
    time.sleep(0.1)
    flushed = s.flush_stale()
    assert len(flushed) == 1
    assert flushed[0].route == "route-f"


def test_flush_stale_ignores_fresh_batches(store: BatchStore) -> None:
    store.add("route-g", {"fresh": True})
    flushed = store.flush_stale()
    assert flushed == []


def test_disabled_config_add_returns_none() -> None:
    s = BatchStore(BatchConfig(enabled=False))
    result = s.add("route-h", {"x": 1})
    assert result is None
    assert s.pending("route-h") == 0


def test_routes_are_independent(store: BatchStore) -> None:
    store.add("r1", {"a": 1})
    store.add("r1", {"a": 2})
    store.add("r2", {"b": 1})
    assert store.pending("r1") == 2
    assert store.pending("r2") == 1
