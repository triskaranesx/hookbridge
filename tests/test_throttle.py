"""Tests for hookbridge.throttle."""

import time

import pytest

from hookbridge.throttle import ThrottleConfig, ThrottleStore


@pytest.fixture()
def store() -> ThrottleStore:
    return ThrottleStore()


PAYLOAD = {"event": "push", "ref": "main"}


def test_first_occurrence_is_not_duplicate(store):
    dup, count = store.is_duplicate("route-a", PAYLOAD)
    assert dup is False
    assert count == 1


def test_second_occurrence_within_window_is_duplicate(store):
    store.is_duplicate("route-a", PAYLOAD)
    dup, count = store.is_duplicate("route-a", PAYLOAD)
    assert dup is True
    assert count == 2


def test_count_increments_on_each_duplicate(store):
    for _ in range(4):
        store.is_duplicate("route-a", PAYLOAD)
    dup, count = store.is_duplicate("route-a", PAYLOAD)
    assert dup is True
    assert count == 5


def test_different_payloads_are_independent(store):
    store.is_duplicate("route-a", PAYLOAD)
    other = {"event": "release"}
    dup, count = store.is_duplicate("route-a", other)
    assert dup is False
    assert count == 1


def test_different_routes_are_independent(store):
    store.is_duplicate("route-a", PAYLOAD)
    dup, _ = store.is_duplicate("route-b", PAYLOAD)
    assert dup is False


def test_disabled_config_never_deduplicates(store):
    store.configure("route-a", ThrottleConfig(enabled=False))
    store.is_duplicate("route-a", PAYLOAD)
    dup, count = store.is_duplicate("route-a", PAYLOAD)
    assert dup is False
    assert count == 1


def test_payload_after_window_expires_is_not_duplicate(store):
    store.configure("route-a", ThrottleConfig(window_seconds=0.05))
    store.is_duplicate("route-a", PAYLOAD)
    time.sleep(0.1)
    dup, count = store.is_duplicate("route-a", PAYLOAD)
    assert dup is False
    assert count == 1


def test_seen_count_returns_none_for_unknown(store):
    assert store.seen_count("route-x", PAYLOAD) is None


def test_seen_count_returns_correct_value(store):
    store.is_duplicate("route-a", PAYLOAD)
    store.is_duplicate("route-a", PAYLOAD)
    assert store.seen_count("route-a", PAYLOAD) == 2


def test_clear_specific_route(store):
    store.is_duplicate("route-a", PAYLOAD)
    store.is_duplicate("route-b", PAYLOAD)
    store.clear("route-a")
    assert store.seen_count("route-a", PAYLOAD) is None
    assert store.seen_count("route-b", PAYLOAD) == 1


def test_clear_all_routes(store):
    store.is_duplicate("route-a", PAYLOAD)
    store.is_duplicate("route-b", PAYLOAD)
    store.clear()
    assert store.seen_count("route-a", PAYLOAD) is None
    assert store.seen_count("route-b", PAYLOAD) is None
