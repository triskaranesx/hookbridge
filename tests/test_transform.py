"""Tests for hookbridge.transform."""

import pytest

from hookbridge.transform import (
    add_metadata,
    apply_template,
    chain,
    drop_keys,
    rename_keys,
)


def test_rename_keys_basic():
    result = rename_keys({"old": 1, "keep": 2}, {"old": "new"})
    assert "new" in result
    assert "old" not in result
    assert result["keep"] == 2


def test_rename_keys_missing_key_ignored():
    result = rename_keys({"a": 1}, {"b": "c"})
    assert result == {"a": 1}


def test_drop_keys_removes_listed():
    result = drop_keys({"a": 1, "b": 2, "c": 3}, ["b", "c"])
    assert result == {"a": 1}


def test_drop_keys_original_unchanged():
    original = {"x": 10, "y": 20}
    drop_keys(original, ["x"])
    assert "x" in original


def test_add_metadata_creates_meta_key():
    result = add_metadata({"data": 1}, {"source": "github"})
    assert result["_meta"]["source"] == "github"
    assert result["data"] == 1


def test_add_metadata_merges_existing_meta():
    payload = {"_meta": {"version": 1}}
    result = add_metadata(payload, {"relay": "hookbridge"})
    assert result["_meta"]["version"] == 1
    assert result["_meta"]["relay"] == "hookbridge"


def test_apply_template_substitutes_placeholders():
    template = {"action": "{event.type}", "static": "hello"}
    payload = {"event": {"type": "push"}}
    result = apply_template(template, payload)
    assert result["action"] == "push"
    assert result["static"] == "hello"


def test_apply_template_missing_path_returns_none():
    template = {"val": "{missing.key}"}
    result = apply_template(template, {})
    assert result["val"] is None


def test_chain_applies_in_order():
    add_x = lambda p: {**p, "x": 1}
    add_y = lambda p: {**p, "y": 2}
    combined = chain(add_x, add_y)
    result = combined({})
    assert result == {"x": 1, "y": 2}
