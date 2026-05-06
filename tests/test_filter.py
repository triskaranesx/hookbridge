"""Tests for hookbridge.filter."""

import pytest

from hookbridge.filter import FilterRule, FilterSet, _get_nested, build_filter_set


# ---------------------------------------------------------------------------
# _get_nested
# ---------------------------------------------------------------------------

def test_get_nested_simple():
    assert _get_nested({"a": 1}, "a") == 1


def test_get_nested_dotted():
    payload = {"event": {"type": "push"}}
    assert _get_nested(payload, "event.type") == "push"


def test_get_nested_missing_returns_none():
    assert _get_nested({"a": 1}, "b.c") is None


# ---------------------------------------------------------------------------
# FilterRule
# ---------------------------------------------------------------------------

def test_filter_rule_glob_match():
    rule = FilterRule(field_path="event", pattern="push*")
    assert rule.matches("push_to_main")
    assert not rule.matches("pull_request")


def test_filter_rule_regex_match():
    rule = FilterRule(field_path="ref", pattern=r"refs/heads/(main|master)", use_regex=True)
    assert rule.matches("refs/heads/main")
    assert not rule.matches("refs/heads/dev")


# ---------------------------------------------------------------------------
# FilterSet
# ---------------------------------------------------------------------------

def test_filter_set_all_rules_must_match():
    fs = FilterSet()
    fs.add_rule(FilterRule("event.type", "push"))
    fs.add_rule(FilterRule("repo.name", "hookbridge*"))

    passing = {"event": {"type": "push"}, "repo": {"name": "hookbridge-core"}}
    failing = {"event": {"type": "push"}, "repo": {"name": "other-repo"}}

    assert fs.evaluate(passing) is True
    assert fs.evaluate(failing) is False


def test_filter_set_empty_passes_everything():
    fs = FilterSet()
    assert fs.evaluate({"any": "payload"}) is True


# ---------------------------------------------------------------------------
# build_filter_set
# ---------------------------------------------------------------------------

def test_build_filter_set_from_config():
    cfg = [{"field": "action", "pattern": "opened"}]
    fs = build_filter_set(cfg)
    assert len(fs.rules) == 1
    assert fs.evaluate({"action": "opened"})
    assert not fs.evaluate({"action": "closed"})
