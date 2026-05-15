"""Tests for hookbridge.circuit_breaker."""

import time
import pytest
from unittest.mock import patch

from hookbridge.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitState,
)


@pytest.fixture
def breaker():
    cb = CircuitBreaker()
    cb.configure("route_a", CircuitBreakerConfig(failure_threshold=3, recovery_timeout=30.0, success_threshold=2))
    return cb


def test_initial_state_is_closed(breaker):
    assert breaker.state_for("route_a") == CircuitState.CLOSED


def test_circuit_opens_after_threshold(breaker):
    for _ in range(3):
        breaker.record_failure("route_a")
    assert breaker.state_for("route_a") == CircuitState.OPEN


def test_is_open_returns_true_when_open(breaker):
    for _ in range(3):
        breaker.record_failure("route_a")
    assert breaker.is_open("route_a") is True


def test_is_open_returns_false_when_closed(breaker):
    assert breaker.is_open("route_a") is False


def test_success_resets_failure_count(breaker):
    breaker.record_failure("route_a")
    breaker.record_failure("route_a")
    breaker.record_success("route_a")
    assert breaker.state_for("route_a") == CircuitState.CLOSED


def test_transitions_to_half_open_after_timeout(breaker):
    for _ in range(3):
        breaker.record_failure("route_a")
    assert breaker.state_for("route_a") == CircuitState.OPEN

    with patch("hookbridge.circuit_breaker.time.monotonic", return_value=time.monotonic() + 31):
        open_now = breaker.is_open("route_a")

    assert open_now is False
    assert breaker.state_for("route_a") == CircuitState.HALF_OPEN


def test_half_open_closes_after_successes(breaker):
    for _ in range(3):
        breaker.record_failure("route_a")
    with patch("hookbridge.circuit_breaker.time.monotonic", return_value=time.monotonic() + 31):
        breaker.is_open("route_a")  # triggers HALF_OPEN
    breaker.record_success("route_a")
    breaker.record_success("route_a")
    assert breaker.state_for("route_a") == CircuitState.CLOSED


def test_half_open_reopens_on_failure(breaker):
    for _ in range(3):
        breaker.record_failure("route_a")
    with patch("hookbridge.circuit_breaker.time.monotonic", return_value=time.monotonic() + 31):
        breaker.is_open("route_a")  # triggers HALF_OPEN
    breaker.record_failure("route_a")
    assert breaker.state_for("route_a") == CircuitState.OPEN


def test_reset_restores_closed_state(breaker):
    for _ in range(3):
        breaker.record_failure("route_a")
    breaker.reset("route_a")
    assert breaker.state_for("route_a") == CircuitState.CLOSED
    assert breaker.is_open("route_a") is False


def test_unknown_route_defaults_to_closed():
    cb = CircuitBreaker()
    assert cb.state_for("new_route") == CircuitState.CLOSED
    assert cb.is_open("new_route") is False
