"""Retry logic for failed webhook deliveries."""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Callable, Awaitable, Optional

logger = logging.getLogger(__name__)


@dataclass
class RetryPolicy:
    """Configuration for retry behavior."""
    max_attempts: int = 3
    base_delay: float = 1.0       # seconds
    max_delay: float = 60.0       # seconds
    backoff_factor: float = 2.0
    jitter: bool = True

    def delay_for(self, attempt: int) -> float:
        """Calculate delay before the given attempt (0-indexed)."""
        if attempt == 0:
            return 0.0
        delay = min(self.base_delay * (self.backoff_factor ** (attempt - 1)), self.max_delay)
        if self.jitter:
            import random
            delay *= 0.5 + random.random() * 0.5
        return delay


@dataclass
class DeliveryAttempt:
    """Record of a single delivery attempt."""
    attempt_number: int
    timestamp: float = field(default_factory=time.time)
    status_code: Optional[int] = None
    error: Optional[str] = None
    success: bool = False


async def deliver_with_retry(
    send_fn: Callable[[], Awaitable[int]],
    policy: Optional[RetryPolicy] = None,
    event_id: str = "unknown",
) -> list[DeliveryAttempt]:
    """
    Attempt delivery using *send_fn*, retrying according to *policy*.

    *send_fn* must be an async callable that returns an HTTP status code.
    Raises the last exception if all attempts are exhausted.
    """
    policy = policy or RetryPolicy()
    attempts: list[DeliveryAttempt] = []

    for attempt in range(policy.max_attempts):
        delay = policy.delay_for(attempt)
        if delay > 0:
            logger.debug("[%s] Waiting %.2fs before attempt %d", event_id, delay, attempt + 1)
            await asyncio.sleep(delay)

        record = DeliveryAttempt(attempt_number=attempt + 1)
        try:
            status_code = await send_fn()
            record.status_code = status_code
            record.success = 200 <= status_code < 300
        except Exception as exc:  # noqa: BLE001
            record.error = str(exc)
            logger.warning("[%s] Attempt %d failed with exception: %s", event_id, attempt + 1, exc)
        finally:
            attempts.append(record)

        if record.success:
            logger.info("[%s] Delivered successfully on attempt %d", event_id, attempt + 1)
            return attempts

        logger.warning(
            "[%s] Attempt %d unsuccessful (status=%s, error=%s)",
            event_id, attempt + 1, record.status_code, record.error,
        )

    logger.error("[%s] All %d attempts exhausted", event_id, policy.max_attempts)
    return attempts
