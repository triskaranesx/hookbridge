"""Validate raw route configuration dicts before passing to :mod:`route_config`."""

from __future__ import annotations

from typing import Any, Dict, List

_VALID_MODES = {"glob", "regex", "exact"}
_VALID_TRANSFORMS = {"rename_keys", "drop_keys", "add_metadata"}


class ConfigError(ValueError):
    """Raised when a route configuration is structurally invalid."""


def _validate_filter(f: Any, idx: int) -> None:
    if not isinstance(f, dict):
        raise ConfigError(f"Filter #{idx} must be a dict, got {type(f).__name__}")
    for key in ("field", "pattern"):
        if key not in f:
            raise ConfigError(f"Filter #{idx} missing required key {key!r}")
    mode = f.get("mode", "glob")
    if mode not in _VALID_MODES:
        raise ConfigError(
            f"Filter #{idx} has invalid mode {mode!r}; choose from {_VALID_MODES}"
        )


def _validate_transform(t: Any, idx: int) -> None:
    if not isinstance(t, dict):
        raise ConfigError(f"Transform #{idx} must be a dict")
    if "type" not in t:
        raise ConfigError(f"Transform #{idx} missing required key 'type'")
    if t["type"] not in _VALID_TRANSFORMS:
        raise ConfigError(
            f"Transform #{idx} has unknown type {t['type']!r}; "
            f"choose from {_VALID_TRANSFORMS}"
        )


def _validate_route(r: Any, idx: int) -> None:
    if not isinstance(r, dict):
        raise ConfigError(f"Route #{idx} must be a dict")
    if "target_url" not in r:
        raise ConfigError(f"Route #{idx} missing required key 'target_url'")
    for i, f in enumerate(r.get("filters", [])):
        _validate_filter(f, i)
    for i, t in enumerate(r.get("transforms", [])):
        _validate_transform(t, i)


def validate_config(config: Dict[str, Any]) -> None:
    """Raise :class:`ConfigError` if *config* fails structural validation."""
    if not isinstance(config, dict):
        raise ConfigError("Top-level config must be a dict")
    for i, route in enumerate(config.get("routes", [])):
        _validate_route(route, i)
