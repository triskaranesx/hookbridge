"""Webhook delivery module: sends payloads to target URLs with retry support."""

from __future__ import annotations

import time
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

import urllib.request
import urllib.error
import json

from hookbridge.retry import RetryPolicy, delay_for, DeliveryAttempt

logger = logging.getLogger(__name__)


@dataclass
class DeliveryResult:
    url: str
    success: bool
    attempts: int
    status_code: Optional[int] = None
    error: Optional[str] = None
    history: list[DeliveryAttempt] = field(default_factory=list)


def _send_once(url: str, payload: Dict[str, Any], headers: Dict[str, str]) -> int:
    """Send a single HTTP POST. Returns HTTP status code."""
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json", **headers},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        return resp.status


def deliver(
    url: str,
    payload: Dict[str, Any],
    policy: Optional[RetryPolicy] = None,
    headers: Optional[Dict[str, str]] = None,
) -> DeliveryResult:
    """Deliver *payload* to *url*, retrying according to *policy*."""
    if policy is None:
        policy = RetryPolicy()
    if headers is None:
        headers = {}

    history: list[DeliveryAttempt] = []
    last_error: Optional[str] = None
    status_code: Optional[int] = None

    for attempt in range(1, policy.max_attempts + 1):
        try:
            status_code = _send_once(url, payload, headers)
            attempt_record = DeliveryAttempt(attempt=attempt, status_code=status_code)
            history.append(attempt_record)
            if status_code < 500:
                logger.info("Delivered to %s on attempt %d (status %d)", url, attempt, status_code)
                return DeliveryResult(
                    url=url,
                    success=True,
                    attempts=attempt,
                    status_code=status_code,
                    history=history,
                )
            last_error = f"server error: {status_code}"
        except (urllib.error.URLError, OSError) as exc:
            last_error = str(exc)
            attempt_record = DeliveryAttempt(attempt=attempt, error=last_error)
            history.append(attempt_record)
            logger.warning("Attempt %d to %s failed: %s", attempt, url, last_error)

        if attempt < policy.max_attempts:
            wait = delay_for(policy, attempt)
            logger.debug("Waiting %.2fs before retry %d", wait, attempt + 1)
            time.sleep(wait)

    return DeliveryResult(
        url=url,
        success=False,
        attempts=policy.max_attempts,
        status_code=status_code,
        error=last_error,
        history=history,
    )
