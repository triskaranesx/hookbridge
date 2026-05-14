"""Tests for hookbridge.ratelimit."""

import time
import pytest
from hookbridge.ratelimit import RateLimiter, RateLimitConfig


@pytest.fixture()
def limiter() -> RateLimiter:
    return RateLimiter()


def test_allow_without_config_always_passes(limiter):
    assert limiter.allow("any_route") is True


def test_allow_disabled_config_always_passes(limiter):
    limiter.configure("r", RateLimitConfig(max_tokens=1, refill_rate=0.0, enabled=False))
    for _ in range(5):
        assert limiter.allow("r") is True


def test_allow_exhausts_burst(limiter):
    limiter.configure("r", RateLimitConfig(max_tokens=3, refill_rate=0.0))
    assert limiter.allow("r") is True
    assert limiter.allow("r") is True
    assert limiter.allow("r") is True
    # bucket empty
    assert limiter.allow("r") is False


def test_remaining_returns_none_for_unknown_route(limiter):
    assert limiter.remaining("unknown") is None


def test_remaining_decrements_on_allow(limiter):
    limiter.configure("r", RateLimitConfig(max_tokens=5, refill_rate=0.0))
    limiter.allow("r")
    limiter.allow("r")
    remaining = limiter.remaining("r")
    assert remaining == pytest.approx(3.0, abs=0.1)


def test_reset_restores_full_bucket(limiter):
    limiter.configure("r", RateLimitConfig(max_tokens=2, refill_rate=0.0))
    limiter.allow("r")
    limiter.allow("r")
    assert limiter.allow("r") is False
    limiter.reset("r")
    assert limiter.allow("r") is True


def test_refill_over_time(limiter, monkeypatch):
    """Tokens should refill proportionally to elapsed time."""
    start = time.monotonic()
    monkeypatch.setattr("time.monotonic", lambda: start)

    limiter.configure("r", RateLimitConfig(max_tokens=5, refill_rate=2.0))
    # drain all tokens
    for _ in range(5):
        limiter.allow("r")
    assert limiter.allow("r") is False

    # advance time by 1 second → 2 tokens refilled
    monkeypatch.setattr("time.monotonic", lambda: start + 1.0)
    assert limiter.allow("r") is True
    assert limiter.allow("r") is True
    assert limiter.allow("r") is False


def test_multiple_routes_isolated(limiter):
    limiter.configure("a", RateLimitConfig(max_tokens=1, refill_rate=0.0))
    limiter.configure("b", RateLimitConfig(max_tokens=3, refill_rate=0.0))
    limiter.allow("a")
    assert limiter.allow("a") is False
    assert limiter.allow("b") is True
