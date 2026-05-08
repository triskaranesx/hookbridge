"""Load router configuration from a plain Python dict (e.g. parsed from YAML/JSON)."""

from __future__ import annotations

from typing import Any, Dict, List

from hookbridge.filter import FilterRule, FilterSet, add_rule
from hookbridge.pipeline import Pipeline, add_transform, build_pipeline
from hookbridge.router import Route, Router, add_route, build_router
from hookbridge.transform import add_metadata, drop_keys, rename_keys

_TRANSFORM_MAP = {
    "rename_keys": rename_keys,
    "drop_keys": drop_keys,
    "add_metadata": add_metadata,
}


def _build_filter_set(rules_cfg: List[Dict[str, Any]]) -> FilterSet:
    fs: FilterSet = FilterSet(rules=[])
    for r in rules_cfg:
        rule = FilterRule(
            field=r["field"],
            pattern=r["pattern"],
            mode=r.get("mode", "glob"),
        )
        add_rule(fs, rule)
    return fs


def _build_pipeline(transforms_cfg: List[Dict[str, Any]]) -> Pipeline:
    pipeline = build_pipeline()
    for t in transforms_cfg:
        name = t["type"]
        if name not in _TRANSFORM_MAP:
            raise ValueError(f"Unknown transform type: {name!r}")
        fn = _TRANSFORM_MAP[name]
        kwargs = {k: v for k, v in t.items() if k != "type"}
        add_transform(pipeline, lambda p, _fn=fn, _kw=kwargs: _fn(p, **_kw))
    return pipeline


def load_routes(config: Dict[str, Any]) -> Router:
    """Build a :class:`Router` from a configuration dictionary.

    Expected shape::

        {"routes": [{"name": "...", "target_url": "...",
                     "filters": [...], "transforms": [...],
                     "enabled": true}]}
    """
    router = build_router()
    for route_cfg in config.get("routes", []):
        fs = _build_filter_set(route_cfg.get("filters", []))
        pipeline = _build_pipeline(route_cfg.get("transforms", []))
        route = Route(
            target_url=route_cfg["target_url"],
            filter_set=fs,
            pipeline=pipeline,
            name=route_cfg.get("name", ""),
            enabled=route_cfg.get("enabled", True),
        )
        add_route(router, route)
    return router
