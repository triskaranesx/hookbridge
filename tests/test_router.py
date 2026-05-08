"""Tests for hookbridge.router."""

from __future__ import annotations

import pytest

from hookbridge.filter import FilterRule, FilterSet, add_rule
from hookbridge.pipeline import build_pipeline
from hookbridge.router import (
    Route,
    Router,
    add_route,
    build_router,
    dispatch,
    set_dispatch_hook,
)


def _make_route(target: str = "http://example.com", pattern: str = "*") -> Route:
    fs = FilterSet(rules=[])
    add_rule(fs, FilterRule(field="event", pattern=pattern, mode="glob"))
    return Route(target_url=target, filter_set=fs, pipeline=build_pipeline())


def test_dispatch_matching_route():
    router = build_router()
    add_route(router, _make_route("http://a.com", "push"))
    results = dispatch(router, {"event": "push", "ref": "main"})
    assert len(results) == 1
    route, payload = results[0]
    assert route.target_url == "http://a.com"
    assert payload["event"] == "push"


def test_dispatch_non_matching_route():
    router = build_router()
    add_route(router, _make_route("http://a.com", "push"))
    results = dispatch(router, {"event": "pull_request"})
    assert results == []


def test_dispatch_multiple_routes_partial_match():
    router = build_router()
    add_route(router, _make_route("http://push.com", "push"))
    add_route(router, _make_route("http://all.com", "*"))
    results = dispatch(router, {"event": "push"})
    assert len(results) == 2
    urls = {r.target_url for r, _ in results}
    assert urls == {"http://push.com", "http://all.com"}


def test_dispatch_disabled_route_skipped():
    router = build_router()
    route = _make_route("http://a.com", "push")
    route.enabled = False
    add_route(router, route)
    results = dispatch(router, {"event": "push"})
    assert results == []


def test_dispatch_hook_called():
    called: list = []
    router = build_router(on_dispatch=lambda r, p: called.append((r.target_url, p)))
    add_route(router, _make_route("http://hook.com", "*"))
    dispatch(router, {"event": "ping"})
    assert len(called) == 1
    assert called[0][0] == "http://hook.com"


def test_dispatch_hook_not_called_on_no_match():
    called: list = []
    router = build_router(on_dispatch=lambda r, p: called.append(r))
    add_route(router, _make_route("http://a.com", "push"))
    dispatch(router, {"event": "delete"})
    assert called == []


def test_build_router_with_routes():
    routes = [_make_route("http://x.com")]
    router = build_router(routes=routes)
    assert len(router.routes) == 1
