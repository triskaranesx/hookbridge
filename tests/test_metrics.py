"""Tests for hookbridge.metrics module."""

import pytest
from hookbridge.metrics import MetricsStore, RouteMetrics


@pytest.fixture()
def store() -> MetricsStore:
    return MetricsStore()


def test_initial_metrics_are_zero(store: MetricsStore) -> None:
    store.record_dispatch("my-route")
    m = store.get("my-route")
    assert m is not None
    assert m.total_dispatched == 1
    assert m.total_delivered == 0
    assert m.total_failed == 0
    assert m.total_retries == 0


def test_record_delivery_increments_delivered(store: MetricsStore) -> None:
    store.record_dispatch("r1")
    store.record_delivery("r1", attempts=1)
    m = store.get("r1")
    assert m.total_delivered == 1
    assert m.total_retries == 0
    assert m.last_success_ts is not None


def test_record_delivery_counts_retries(store: MetricsStore) -> None:
    store.record_dispatch("r1")
    store.record_delivery("r1", attempts=3)
    m = store.get("r1")
    assert m.total_retries == 2


def test_record_failure_increments_failed(store: MetricsStore) -> None:
    store.record_dispatch("r2")
    store.record_failure("r2", attempts=3)
    m = store.get("r2")
    assert m.total_failed == 1
    assert m.total_retries == 2
    assert m.last_failure_ts is not None


def test_success_rate_calculation(store: MetricsStore) -> None:
    for _ in range(4):
        store.record_dispatch("r3")
    store.record_delivery("r3", attempts=1)
    store.record_delivery("r3", attempts=1)
    store.record_failure("r3", attempts=1)
    store.record_failure("r3", attempts=1)
    m = store.get("r3")
    assert m.success_rate == pytest.approx(0.5)


def test_success_rate_zero_when_no_dispatches(store: MetricsStore) -> None:
    m = RouteMetrics(route_name="empty")
    assert m.success_rate == 0.0


def test_get_returns_none_for_unknown_route(store: MetricsStore) -> None:
    assert store.get("nonexistent") is None


def test_all_routes_returns_all(store: MetricsStore) -> None:
    store.record_dispatch("a")
    store.record_dispatch("b")
    names = {m.route_name for m in store.all_routes()}
    assert names == {"a", "b"}


def test_reset_single_route(store: MetricsStore) -> None:
    store.record_dispatch("a")
    store.record_dispatch("b")
    store.reset("a")
    assert store.get("a") is None
    assert store.get("b") is not None


def test_reset_all_routes(store: MetricsStore) -> None:
    store.record_dispatch("a")
    store.record_dispatch("b")
    store.reset()
    assert store.all_routes() == []
