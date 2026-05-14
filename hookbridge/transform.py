"""Payload transformation utilities."""

from __future__ import annotations

import copy
from typing import Any


def rename_keys(payload: dict[str, Any], mapping: dict[str, str]) -> dict[str, Any]:
    """Return a shallow copy of *payload* with keys renamed per *mapping*."""
    result = copy.copy(payload)
    for old_key, new_key in mapping.items():
        if old_key in result:
            result[new_key] = result.pop(old_key)
    return result


def drop_keys(payload: dict[str, Any], keys: list[str]) -> dict[str, Any]:
    """Return a copy of *payload* without the specified *keys*."""
    return {k: v for k, v in payload.items() if k not in keys}


def keep_keys(payload: dict[str, Any], keys: list[str]) -> dict[str, Any]:
    """Return a copy of *payload* containing only the specified *keys*.

    Keys listed in *keys* that are absent from *payload* are silently ignored.

    Example::

        >>> keep_keys({"a": 1, "b": 2, "c": 3}, ["a", "c"])
        {'a': 1, 'c': 3}
    """
    return {k: v for k, v in payload.items() if k in keys}


def add_metadata(payload: dict[str, Any], metadata: dict[str, Any]) -> dict[str, Any]:
    """Merge *metadata* into a copy of *payload* under the '_meta' key."""
    result = copy.copy(payload)
    result.setdefault("_meta", {})
    result["_meta"].update(metadata)
    return result


def apply_template(template: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    """Recursively substitute ``{field.path}`` placeholders in *template*
    with values drawn from *payload* using dot-notation lookup."""
    from hookbridge.filter import _get_nested

    def _resolve(obj: Any) -> Any:
        if isinstance(obj, str):
            if obj.startswith("{") and obj.endswith("}"):
                path = obj[1:-1]
                return _get_nested(payload, path)
            return obj
        if isinstance(obj, dict):
            return {k: _resolve(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [_resolve(item) for item in obj]
        return obj

    return _resolve(template)  # type: ignore[return-value]


def chain(*transforms):
    """Return a function that applies each transform in sequence."""
    def _apply(payload: dict[str, Any]) -> dict[str, Any]:
        result = payload
        for fn in transforms:
            result = fn(result)
        return result
    return _apply
