"""Combines filtering and transformation into a single processing pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from hookbridge.filter import FilterSet


@dataclass
class Pipeline:
    """Process an incoming webhook payload through filter then transform steps."""

    filter_set: FilterSet = field(default_factory=FilterSet)
    transforms: list[Callable[[dict[str, Any]], dict[str, Any]]] = field(
        default_factory=list
    )

    def add_transform(self, fn: Callable[[dict[str, Any]], dict[str, Any]]) -> None:
        """Append a transform callable to the pipeline."""
        self.transforms.append(fn)

    def process(self, payload: dict[str, Any]) -> dict[str, Any] | None:
        """Run the payload through the pipeline.

        Returns the (possibly transformed) payload, or ``None`` if the
        payload is rejected by the filter set.
        """
        if not self.filter_set.evaluate(payload):
            return None

        result = payload
        for transform in self.transforms:
            result = transform(result)
        return result


def build_pipeline(
    filter_rules: list[dict[str, Any]],
    transforms: list[Callable[[dict[str, Any]], dict[str, Any]]] | None = None,
) -> Pipeline:
    """Convenience factory used by the route/config layer."""
    from hookbridge.filter import build_filter_set

    fs = build_filter_set(filter_rules)
    pipeline = Pipeline(filter_set=fs)
    for fn in transforms or []:
        pipeline.add_transform(fn)
    return pipeline
