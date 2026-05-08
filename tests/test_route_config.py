"""Tests for hookbridge.route_config."""

from __future__ import annotations

import pytest

from hookbridge.route_config import load_routes
from hookbridge.router import dispatch


_SAMPLE_CONFIG = {
    "routes": [
        {
            "name": "push-handler",
            "target_url": "http://receiver.example.com/push",
            "enabled": True,
            "filters": [
                {"field": "event", "pattern": "push", "mode": "glob"}
            ],
            "transforms": [
                {"type": "drop_keys", "keys": ["secret"]},
                {"type": "add_metadata", "source": "hookbridge"},
            ],
        },
        {
            "name": "disabled-route",
            "target_url": "http://disabled.example.com",
            "enabled": False,
            "filters": [],
            "transforms": [],
        },
    ]
}


def test_load_routes_creates_router():
    router = load_routes(_SAMPLE_CONFIG)
    assert len(router.routes) == 2


def test_load_routes_route_names():
    router = load_routes(_SAMPLE_CONFIG)
    names = [r.name for r in router.routes]
    assert "push-handler" in names
    assert "disabled-route" in names


def test_load_routes_filter_applied():
    router = load_routes(_SAMPLE_CONFIG)
    results = dispatch(router, {"event": "push", "secret": "abc", "ref": "main"})
    assert len(results) == 1
    route, payload = results[0]
    assert route.name == "push-handler"
    assert "secret" not in payload


def test_load_routes_disabled_route_skipped():
    router = load_routes(_SAMPLE_CONFIG)
    results = dispatch(router, {"event": "anything"})
    urls = [r.target_url for r, _ in results]
    assert "http://disabled.example.com" not in urls


def test_load_routes_metadata_added():
    router = load_routes(_SAMPLE_CONFIG)
    results = dispatch(router, {"event": "push"})
    _, payload = results[0]
    assert "_meta" in payload
    assert payload["_meta"]["source"] == "hookbridge"


def test_load_routes_unknown_transform_raises():
    bad_config = {
        "routes": [
            {
                "target_url": "http://x.com",
                "filters": [],
                "transforms": [{"type": "nonexistent"}],
            }
        ]
    }
    with pytest.raises(ValueError, match="Unknown transform type"):
        load_routes(bad_config)


def test_load_routes_empty_config():
    router = load_routes({})
    assert router.routes == []
