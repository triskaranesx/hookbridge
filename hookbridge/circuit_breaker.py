"""Per-route circuit breaker to stop delivery attempts when a target is unhealthy."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Optional


class CircuitState(str, Enum):
    CLOSED = "closed"      # normal operation
    OPEN = "open"          # blocking requests
    HALF_OPEN = "half_open"  # testing recovery


@dataclass
class CircuitBreakerConfig:
    failure_threshold: int = 5      # failures before opening
    recovery_timeout: float = 30.0  # seconds before attempting half-open
    success_threshold: int = 2      # successes in half-open before closing


@dataclass
class _CircuitState:
    state: CircuitState = CircuitState.CLOSED
    failure_count: int = 0
    success_count: int = 0
    opened_at: Optional[float] = None


@dataclass
class CircuitBreaker:
    _config: CircuitBreakerConfig = field(default_factory=CircuitBreakerConfig)
    _circuits: Dict[str, _CircuitState] = field(default_factory=dict)

    def configure(self, route: str, config: CircuitBreakerConfig) -> None:
        self._config = config
        self._circuits.setdefault(route, _CircuitState())

    def _get(self, route: str) -> _CircuitState:
        if route not in self._circuits:
            self._circuits[route] = _CircuitState()
        return self._circuits[route]

    def is_open(self, route: str) -> bool:
        """Return True if the circuit is open (requests should be blocked)."""
        c = self._get(route)
        if c.state == CircuitState.OPEN:
            if time.monotonic() - (c.opened_at or 0) >= self._config.recovery_timeout:
                c.state = CircuitState.HALF_OPEN
                c.success_count = 0
                return False
            return True
        return False

    def record_success(self, route: str) -> None:
        c = self._get(route)
        if c.state == CircuitState.HALF_OPEN:
            c.success_count += 1
            if c.success_count >= self._config.success_threshold:
                c.state = CircuitState.CLOSED
                c.failure_count = 0
                c.success_count = 0
        elif c.state == CircuitState.CLOSED:
            c.failure_count = 0

    def record_failure(self, route: str) -> None:
        c = self._get(route)
        if c.state == CircuitState.HALF_OPEN:
            c.state = CircuitState.OPEN
            c.opened_at = time.monotonic()
            return
        c.failure_count += 1
        if c.failure_count >= self._config.failure_threshold:
            c.state = CircuitState.OPEN
            c.opened_at = time.monotonic()

    def state_for(self, route: str) -> CircuitState:
        return self._get(route).state

    def reset(self, route: str) -> None:
        self._circuits[route] = _CircuitState()
