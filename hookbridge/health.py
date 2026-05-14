"""Health check and status reporting for hookbridge."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from hookbridge.metrics import MetricsStore


@dataclass
class ComponentStatus:
    name: str
    healthy: bool
    detail: str = ""


@dataclass
class HealthReport:
    healthy: bool
    timestamp: str
    components: list[ComponentStatus] = field(default_factory=list)
    summary: dict[str, Any] = field(default_factory=dict)


def _check_metrics(store: MetricsStore) -> ComponentStatus:
    """Inspect the metrics store for obvious anomalies."""
    try:
        all_metrics = store.all()
        total_routes = len(all_metrics)
        degraded = [
            name
            for name, m in all_metrics.items()
            if m.dispatched > 0 and (m.failed / m.dispatched) > 0.5
        ]
        if degraded:
            return ComponentStatus(
                name="metrics",
                healthy=False,
                detail=f"High failure rate on routes: {', '.join(degraded)}",
            )
        return ComponentStatus(
            name="metrics",
            healthy=True,
            detail=f"{total_routes} route(s) tracked",
        )
    except Exception as exc:  # pragma: no cover
        return ComponentStatus(name="metrics", healthy=False, detail=str(exc))


def _utc_now() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def build_report(store: MetricsStore) -> HealthReport:
    """Build a full health report from available components."""
    components: list[ComponentStatus] = []

    metrics_status = _check_metrics(store)
    components.append(metrics_status)

    overall_healthy = all(c.healthy for c in components)

    all_metrics = store.all()
    total_dispatched = sum(m.dispatched for m in all_metrics.values())
    total_delivered = sum(m.delivered for m in all_metrics.values())
    total_failed = sum(m.failed for m in all_metrics.values())

    summary = {
        "routes_tracked": len(all_metrics),
        "total_dispatched": total_dispatched,
        "total_delivered": total_delivered,
        "total_failed": total_failed,
    }

    return HealthReport(
        healthy=overall_healthy,
        timestamp=_utc_now(),
        components=components,
        summary=summary,
    )


def report_as_dict(report: HealthReport) -> dict[str, Any]:
    """Serialise a HealthReport to a plain dictionary."""
    return {
        "healthy": report.healthy,
        "timestamp": report.timestamp,
        "components": [
            {"name": c.name, "healthy": c.healthy, "detail": c.detail}
            for c in report.components
        ],
        "summary": report.summary,
    }
