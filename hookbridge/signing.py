"""HMAC-based webhook signature verification and generation."""

import hashlib
import hmac
import time
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class SigningConfig:
    secret: str
    algorithm: str = "sha256"
    header: str = "X-Hub-Signature-256"
    timestamp_header: Optional[str] = "X-Hook-Timestamp"
    max_age_seconds: int = 300


def _digest(secret: str, algorithm: str, body: bytes) -> str:
    """Compute HMAC digest and return as hex string."""
    mac = hmac.new(secret.encode(), body, getattr(hashlib, algorithm))
    return f"{algorithm}={mac.hexdigest()}"


def sign(config: SigningConfig, body: bytes) -> dict[str, str]:
    """Return headers dict containing signature (and optional timestamp)."""
    headers: dict[str, str] = {}
    if config.timestamp_header:
        headers[config.timestamp_header] = str(int(time.time()))
    headers[config.header] = _digest(config.secret, config.algorithm, body)
    return headers


def verify(
    config: SigningConfig,
    body: bytes,
    signature: str,
    timestamp: Optional[str] = None,
) -> bool:
    """Return True if signature is valid (and timestamp is fresh, if provided)."""
    if config.timestamp_header and timestamp is not None:
        try:
            ts = int(timestamp)
        except ValueError:
            return False
        age = int(time.time()) - ts
        if age < 0 or age > config.max_age_seconds:
            return False

    expected = _digest(config.secret, config.algorithm, body)
    return hmac.compare_digest(expected, signature)
