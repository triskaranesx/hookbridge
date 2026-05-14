"""Tests for hookbridge.signing."""

import hashlib
import hmac
import time

import pytest

from hookbridge.signing import SigningConfig, _digest, sign, verify


SECRET = "supersecret"
BODY = b'{"event": "push"}'


@pytest.fixture
def cfg() -> SigningConfig:
    return SigningConfig(secret=SECRET)


def _expected(secret: str, algo: str, body: bytes) -> str:
    mac = hmac.new(secret.encode(), body, getattr(hashlib, algo))
    return f"{algo}={mac.hexdigest()}"


def test_digest_produces_correct_hmac(cfg):
    result = _digest(SECRET, "sha256", BODY)
    assert result == _expected(SECRET, "sha256", BODY)


def test_sign_returns_signature_header(cfg):
    headers = sign(cfg, BODY)
    assert cfg.header in headers
    assert headers[cfg.header].startswith("sha256=")


def test_sign_includes_timestamp_header(cfg):
    before = int(time.time())
    headers = sign(cfg, BODY)
    after = int(time.time())
    ts = int(headers[cfg.timestamp_header])
    assert before <= ts <= after


def test_sign_no_timestamp_header_when_disabled():
    cfg = SigningConfig(secret=SECRET, timestamp_header=None)
    headers = sign(cfg, BODY)
    assert len(headers) == 1
    assert cfg.header in headers


def test_verify_valid_signature(cfg):
    headers = sign(cfg, BODY)
    sig = headers[cfg.header]
    ts = headers[cfg.timestamp_header]
    assert verify(cfg, BODY, sig, timestamp=ts) is True


def test_verify_wrong_secret():
    cfg2 = SigningConfig(secret="wrongsecret")
    headers = sign(cfg, BODY)
    sig = headers[cfg.header]
    ts = headers[cfg.timestamp_header]
    assert verify(cfg2, BODY, sig, timestamp=ts) is False


def test_verify_tampered_body(cfg):
    headers = sign(cfg, BODY)
    sig = headers[cfg.header]
    ts = headers[cfg.timestamp_header]
    assert verify(cfg, b'{"event": "delete"}', sig, timestamp=ts) is False


def test_verify_expired_timestamp(cfg):
    old_ts = str(int(time.time()) - 400)
    sig = _expected(SECRET, "sha256", BODY)
    assert verify(cfg, BODY, sig, timestamp=old_ts) is False


def test_verify_invalid_timestamp_string(cfg):
    sig = _expected(SECRET, "sha256", BODY)
    assert verify(cfg, BODY, sig, timestamp="not-a-number") is False


def test_verify_skips_timestamp_check_when_not_provided():
    cfg = SigningConfig(secret=SECRET, timestamp_header=None)
    sig = _expected(SECRET, "sha256", BODY)
    assert verify(cfg, BODY, sig, timestamp=None) is True
