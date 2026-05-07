"""Tests for hookbridge.delivery module."""

from __future__ import annotations

from unittest.mock import patch, MagicMock
import urllib.error

import pytest

from hookbridge.delivery import deliver, DeliveryResult
from hookbridge.retry import RetryPolicy


def _make_response(status: int):
    mock_resp = MagicMock()
    mock_resp.status = status
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)
    return mock_resp


@patch("hookbridge.delivery.time.sleep")
@patch("hookbridge.delivery.urllib.request.urlopen")
def test_deliver_success_first_attempt(mock_urlopen, mock_sleep):
    mock_urlopen.return_value = _make_response(200)
    policy = RetryPolicy(max_attempts=3)
    result = deliver("http://example.com/hook", {"event": "push"}, policy=policy)

    assert result.success is True
    assert result.attempts == 1
    assert result.status_code == 200
    mock_sleep.assert_not_called()


@patch("hookbridge.delivery.time.sleep")
@patch("hookbridge.delivery.urllib.request.urlopen")
def test_deliver_retries_on_server_error(mock_urlopen, mock_sleep):
    mock_urlopen.side_effect = [
        _make_response(503),
        _make_response(503),
        _make_response(200),
    ]
    policy = RetryPolicy(max_attempts=3, base_delay=0.1)
    result = deliver("http://example.com/hook", {"event": "push"}, policy=policy)

    assert result.success is True
    assert result.attempts == 3
    assert mock_sleep.call_count == 2


@patch("hookbridge.delivery.time.sleep")
@patch("hookbridge.delivery.urllib.request.urlopen")
def test_deliver_fails_after_all_attempts(mock_urlopen, mock_sleep):
    mock_urlopen.side_effect = urllib.error.URLError("connection refused")
    policy = RetryPolicy(max_attempts=3, base_delay=0.0)
    result = deliver("http://example.com/hook", {"x": 1}, policy=policy)

    assert result.success is False
    assert result.attempts == 3
    assert result.error is not None
    assert len(result.history) == 3


@patch("hookbridge.delivery.time.sleep")
@patch("hookbridge.delivery.urllib.request.urlopen")
def test_deliver_4xx_treated_as_success(mock_urlopen, mock_sleep):
    """4xx responses are not retried — treat as a definitive (non-5xx) response."""
    mock_urlopen.return_value = _make_response(400)
    policy = RetryPolicy(max_attempts=3)
    result = deliver("http://example.com/hook", {}, policy=policy)

    assert result.success is True
    assert result.status_code == 400
    assert result.attempts == 1


@patch("hookbridge.delivery.time.sleep")
@patch("hookbridge.delivery.urllib.request.urlopen")
def test_deliver_uses_default_policy_when_none(mock_urlopen, mock_sleep):
    mock_urlopen.return_value = _make_response(201)
    result = deliver("http://example.com/hook", {})

    assert isinstance(result, DeliveryResult)
    assert result.success is True


@patch("hookbridge.delivery.time.sleep")
@patch("hookbridge.delivery.urllib.request.urlopen")
def test_deliver_history_records_all_attempts(mock_urlopen, mock_sleep):
    mock_urlopen.side_effect = [
        _make_response(500),
        _make_response(200),
    ]
    policy = RetryPolicy(max_attempts=2, base_delay=0.0)
    result = deliver("http://example.com/hook", {"k": "v"}, policy=policy)

    assert len(result.history) == 2
    assert result.history[0].status_code == 500
    assert result.history[1].status_code == 200
