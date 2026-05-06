"""Payload filtering for webhook events."""

from __future__ import annotations

import fnmatch
import re
from dataclasses import dataclass, field
from typing import Any


@dataclass
class FilterRule:
    """A single filter rule that matches against a payload field."""

    field_path: str  # dot-separated path, e.g. "event.type"
    pattern: str     # glob or regex pattern
    use_regex: bool = False

    def matches(self, value: Any) -> bool:
        """Return True if *value* satisfies this rule."""
        text = str(value)
        if self.use_regex:
            return bool(re.search(self.pattern, text))
        return fnmatch.fnmatch(text, self.pattern)


@dataclass
class FilterSet:
    """Collection of FilterRules applied with AND semantics."""

    rules: list[FilterRule] = field(default_factory=list)

    def add_rule(self, rule: FilterRule) -> None:
        self.rules.append(rule)

    def evaluate(self, payload: dict[str, Any]) -> bool:
        """Return True only if *all* rules match the payload."""
        for rule in self.rules:
            value = _get_nested(payload, rule.field_path)
            if value is None or not rule.matches(value):
                return False
        return True


def _get_nested(payload: dict[str, Any], path: str) -> Any:
    """Retrieve a value from a nested dict using dot notation."""
    parts = path.split(".")
    current: Any = payload
    for part in parts:
        if not isinstance(current, dict):
            return None
        current = current.get(part)
    return current


def build_filter_set(rules_config: list[dict[str, Any]]) -> FilterSet:
    """Build a FilterSet from a list of rule dicts (e.g. from YAML/JSON config)."""
    fs = FilterSet()
    for cfg in rules_config:
        fs.add_rule(
            FilterRule(
                field_path=cfg["field"],
                pattern=cfg["pattern"],
                use_regex=cfg.get("regex", False),
            )
        )
    return fs
