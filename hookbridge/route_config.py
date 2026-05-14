"""Load and build Route objects from a validated config dict."""

from __future__ import annotations

from typing import Any, Dict, List

from hookbridge.filter import FilterSet, add_rule
from hookbridge.pipeline import Pipeline, add_transform, build_pipeline
from hookbridge.ratelimit import RateLimiter, RateLimitConfig
from hookbridge.router import Router, Route, add_route
from hookbridge.transform import rename_keys, drop_keys, keep_keys, add_metadata


def _build_filter_set(filter_cfg: List[Dict[str, Any]]) -> FilterSet:
    fs: FilterSet = FilterSet(rules=[])
    for rule in filter_cfg:
        fs = add_rule(fs, rule["field"], rule["pattern"], rule.get("mode", "glob"))
    return fs


def _build_pipeline(transform_cfg: List[Dict[str, Any]]) -> Pipeline:
    pipeline: Pipeline = Pipeline(transforms=[])
    for step in transform_cfg:
        op = step.get("op")
        if op == "rename":
            pipeline = add_transform(pipeline, lambda p, s=step: rename_keys(p, s["mapping"]))
        elif op == "drop":
            pipeline = add_transform(pipeline, lambda p, s=step: drop_keys(p, s["keys"]))
        elif op == "keep":
            pipeline = add_transform(pipeline, lambda p, s=step: keep_keys(p, s["keys"]))
        elif op == "metadata":
            pipeline = add_transform(pipeline, lambda p, s=step: add_metadata(p, s.get("meta", {})))
    return pipeline


def _build_rate_limiter(routes_cfg: List[Dict[str, Any]]) -> RateLimiter:
    rl = RateLimiter()
    for route_cfg in routes_cfg:
        rl_cfg = route_cfg.get("rate_limit")
        if rl_cfg:
            rl.configure(
                route_cfg["name"],
                RateLimitConfig(
                    max_tokens=rl_cfg.get("max_tokens", 10),
                    refill_rate=rl_cfg.get("refill_rate", 1.0),
                    enabled=rl_cfg.get("enabled", True),
                ),
            )
    return rl


def load_routes(config: Dict[str, Any]) -> tuple[Router, RateLimiter]:
    """Build a Router and a RateLimiter from a validated config dict."""
    router: Router = Router(routes=[])
    routes_cfg: List[Dict[str, Any]] = config.get("routes", [])

    for route_cfg in routes_cfg:
        if not route_cfg.get("enabled", True):
            continue

        filter_set = _build_filter_set(route_cfg.get("filters", []))
        pipeline = _build_pipeline(route_cfg.get("transforms", []))

        route = Route(
            name=route_cfg["name"],
            target_url=route_cfg["target_url"],
            filter_set=filter_set,
            pipeline=build_pipeline(pipeline),
            enabled=True,
        )
        router = add_route(router, route)

    rate_limiter = _build_rate_limiter(routes_cfg)
    return router, rate_limiter
