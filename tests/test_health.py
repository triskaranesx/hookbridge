"""Tests for hookbridge.health."""

from hookbridge.health import (
    ComponentStatus,
    HealthReport,
    build_report,
    report_as_dict,
)
from hookbridge.metrics import MetricsStore


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _store_with_data(
    route: str = "r1",
    dispatched: int = 0,
    delivered: int = 0,
    failed: int = 0,
    retries: int = 0,
) -> MetricsStore:
    store = MetricsStore()
    for _ in range(dispatched):
        store.record_dispatch(route)
    for _ in range(delivered):
        store.record_delivery(route, attempts=1 + retries)
    for _ in range(failed):
        store.record_failure(route)
    return store


# ---------------------------------------------------------------------------
# ComponentStatus
# ---------------------------------------------------------------------------

def test_component_status_defaults():
    cs = ComponentStatus(name="x", healthy=True)
    assert cs.detail == ""


# ---------------------------------------------------------------------------
# build_report — empty store
# ---------------------------------------------------------------------------

def test_build_report_empty_store_is_healthy():
    store = MetricsStore()
    report = build_report(store)
    assert report.healthy is True


def test_build_report_empty_store_summary_zeros():
    store = MetricsStore()
    report = build_report(store)
    assert report.summary["total_dispatched"] == 0
    assert report.summary["total_delivered"] == 0
    assert report.summary["total_failed"] == 0


def test_build_report_has_timestamp():
    store = MetricsStore()
    report = build_report(store)
    assert "T" in report.timestamp  # ISO-8601 format


# ---------------------------------------------------------------------------
# build_report — healthy routes
# ---------------------------------------------------------------------------

def test_build_report_healthy_routes():
    store = _store_with_data(dispatched=10, delivered=9, failed=1)
    report = build_report(store)
    assert report.healthy is True
    assert report.summary["total_dispatched"] == 10


def test_build_report_tracks_route_count():
    store = MetricsStore()
    store.record_dispatch("a")
    store.record_dispatch("b")
    report = build_report(store)
    assert report.summary["routes_tracked"] == 2


# ---------------------------------------------------------------------------
# build_report — degraded route triggers unhealthy
# ---------------------------------------------------------------------------

def test_build_report_high_failure_rate_unhealthy():
    store = MetricsStore()
    for _ in range(10):
        store.record_dispatch("bad_route")
    for _ in range(8):
        store.record_failure("bad_route")
    report = build_report(store)
    assert report.healthy is False


def test_build_report_degraded_component_detail_mentions_route():
    store = MetricsStore()
    for _ in range(4):
        store.record_dispatch("flaky")
    for _ in range(3):
        store.record_failure("flaky")
    report = build_report(store)
    metrics_component = next(c for c in report.components if c.name == "metrics")
    assert "flaky" in metrics_component.detail


# ---------------------------------------------------------------------------
# report_as_dict
# ---------------------------------------------------------------------------

def test_report_as_dict_keys():
    store = MetricsStore()
    d = report_as_dict(build_report(store))
    assert set(d.keys()) == {"healthy", "timestamp", "components", "summary"}


def test_report_as_dict_components_structure():
    store = MetricsStore()
    d = report_as_dict(build_report(store))
    for comp in d["components"]:
        assert "name" in comp
        assert "healthy" in comp
        assert "detail" in comp
