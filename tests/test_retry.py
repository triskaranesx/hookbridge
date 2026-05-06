"""Tests for hookbridge.retry module."""

import asyncio
import pytest
from unittest.mock import AsyncMock, patch

from hookbridge.retry import RetryPolicy, DeliveryAttempt, deliver_with_retry


# ---------------------------------------------------------------------------
# RetryPolicy
# ---------------------------------------------------------------------------

def test_retry_policy_defaults():
    policy = RetryPolicy()
    assert policy.max_attempts == 3
    assert policy.delay_for(0) == 0.0


def test_retry_policy_delay_increases():
    policy = RetryPolicy(base_delay=1.0, backoff_factor=2.0, jitter=False)
    assert policy.delay_for(1) == pytest.approx(1.0)
    assert policy.delay_for(2) == pytest.approx(2.0)
    assert policy.delay_for(3) == pytest.approx(4.0)


def test_retry_policy_max_delay_capped():
    policy = RetryPolicy(base_delay=10.0, max_delay=15.0, backoff_factor=3.0, jitter=False)
    assert policy.delay_for(4) <= 15.0


# ---------------------------------------------------------------------------
# deliver_with_retry
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_success_on_first_attempt():
    send_fn = AsyncMock(return_value=200)
    with patch("hookbridge.retry.asyncio.sleep", new_callable=AsyncMock):
        attempts = await deliver_with_retry(send_fn, event_id="evt-1")

    assert len(attempts) == 1
    assert attempts[0].success is True
    assert attempts[0].status_code == 200
    send_fn.assert_awaited_once()


@pytest.mark.asyncio
async def test_success_after_retries():
    send_fn = AsyncMock(side_effect=[500, 503, 200])
    policy = RetryPolicy(max_attempts=3, base_delay=0.0, jitter=False)
    with patch("hookbridge.retry.asyncio.sleep", new_callable=AsyncMock):
        attempts = await deliver_with_retry(send_fn, policy=policy, event_id="evt-2")

    assert len(attempts) == 3
    assert attempts[-1].success is True
    assert [a.status_code for a in attempts] == [500, 503, 200]


@pytest.mark.asyncio
async def test_all_attempts_fail():
    send_fn = AsyncMock(return_value=500)
    policy = RetryPolicy(max_attempts=3, base_delay=0.0, jitter=False)
    with patch("hookbridge.retry.asyncio.sleep", new_callable=AsyncMock):
        attempts = await deliver_with_retry(send_fn, policy=policy, event_id="evt-3")

    assert len(attempts) == 3
    assert all(not a.success for a in attempts)


@pytest.mark.asyncio
async def test_exception_recorded():
    send_fn = AsyncMock(side_effect=ConnectionError("timeout"))
    policy = RetryPolicy(max_attempts=2, base_delay=0.0, jitter=False)
    with patch("hookbridge.retry.asyncio.sleep", new_callable=AsyncMock):
        attempts = await deliver_with_retry(send_fn, policy=policy, event_id="evt-4")

    assert len(attempts) == 2
    assert all(a.error == "timeout" for a in attempts)
    assert all(not a.success for a in attempts)
