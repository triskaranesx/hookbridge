"""Route incoming webhooks to one or more delivery targets based on rules."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, List, Optional

from hookbridge.filter import FilterSet, evaluate
from hookbridge.pipeline import Pipeline, process


@dataclass
class Route:
    """A single routing rule mapping a filter set and pipeline to a target URL."""

    target_url: str
    filter_set: FilterSet
    pipeline: Pipeline
    name: str = ""
    enabled: bool = True


@dataclass
class Router:
    """Holds all registered routes and dispatches payloads."""

    routes: List[Route] = field(default_factory=list)
    _on_dispatch: Optional[Callable[[Route, dict], Any]] = field(
        default=None, repr=False
    )


def add_route(router: Router, route: Route) -> None:
    """Register a new route on the router."""
    router.routes.append(route)


def set_dispatch_hook(
    router: Router, hook: Callable[[Route, dict], Any]
) -> None:
    """Set a callback invoked for every matched (route, payload) pair."""
    router._on_dispatch = hook


def dispatch(router: Router, payload: dict) -> List[tuple[Route, dict]]:
    """Evaluate all routes against *payload*.

    Returns a list of ``(route, transformed_payload)`` pairs for every
    enabled route whose filter set matches the payload.
    """
    results: List[tuple[Route, dict]] = []
    for route in router.routes:
        if not route.enabled:
            continue
        if not evaluate(route.filter_set, payload):
            continue
        transformed = process(route.pipeline, payload)
        if router._on_dispatch is not None:
            router._on_dispatch(route, transformed)
        results.append((route, transformed))
    return results


def build_router(
    routes: Optional[List[Route]] = None,
    on_dispatch: Optional[Callable[[Route, dict], Any]] = None,
) -> Router:
    """Convenience factory for creating a fully configured :class:`Router`."""
    router = Router(routes=list(routes or []))
    if on_dispatch is not None:
        set_dispatch_hook(router, on_dispatch)
    return router
