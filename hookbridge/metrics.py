"""Simple in-memory metrics collection for hookbridge delivery tracking."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Dict


@dataclass
class RouteMetrics:
    route_name: str
    total_dispatched: int = 0
    total_delivered: int = 0
    total_failed: int = 0
    total_retries: int = 0
    last_success_ts: float | None = None
    last_failure_ts: float | None = None

    @property
    def success_rate(self) -> float:
        if self.total_dispatched == 0:
            return 0.0
        return self.total_delivered / self.total_dispatched


@dataclass
class MetricsStore:
    _routes: Dict[str, RouteMetrics] = field(default_factory=dict)

    def _get_or_create(self, route_name: str) -> RouteMetrics:
        if route_name not in self._routes:
            self._routes[route_name] = RouteMetrics(route_name=route_name)
        return self._routes[route_name]

    def record_dispatch(self, route_name: str) -> None:
        m = self._get_or_create(route_name)
        m.total_dispatched += 1

    def record_delivery(self, route_name: str, attempts: int) -> None:
        m = self._get_or_create(route_name)
        m.total_delivered += 1
        m.total_retries += max(0, attempts - 1)
        m.last_success_ts = time.time()

    def record_failure(self, route_name: str, attempts: int) -> None:
        m = self._get_or_create(route_name)
        m.total_failed += 1
        m.total_retries += max(0, attempts - 1)
        m.last_failure_ts = time.time()

    def get(self, route_name: str) -> RouteMetrics | None:
        return self._routes.get(route_name)

    def all_routes(self) -> list[RouteMetrics]:
        return list(self._routes.values())

    def reset(self, route_name: str | None = None) -> None:
        if route_name is not None:
            self._routes.pop(route_name, None)
        else:
            self._routes.clear()


_default_store = MetricsStore()


def get_default_store() -> MetricsStore:
    return _default_store
