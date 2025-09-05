"""Conserved span-level fictional cost and optimization attribution."""

from __future__ import annotations

from dataclasses import dataclass


class AttributionError(ValueError):
    """Raised when cost components do not conserve."""


@dataclass(frozen=True, slots=True)
class Cost:
    prompt_micros: int = 0
    completion_micros: int = 0
    cache_saved_micros: int = 0
    batch_saved_micros: int = 0
    adjustment_micros: int = 0

    def __post_init__(self) -> None:
        values = (
            self.prompt_micros,
            self.completion_micros,
            self.cache_saved_micros,
            self.batch_saved_micros,
        )
        if any(
            isinstance(value, bool) or not isinstance(value, int) or value < 0 for value in values
        ) or not isinstance(self.adjustment_micros, int):
            raise AttributionError("cost: components must use valid integer micro-units")

    @property
    def gross_micros(self) -> int:
        return self.prompt_micros + self.completion_micros

    @property
    def net_micros(self) -> int:
        return (
            self.gross_micros
            - self.cache_saved_micros
            - self.batch_saved_micros
            + self.adjustment_micros
        )


def add_costs(costs: tuple[Cost, ...]) -> Cost:
    """Add each attribution component independently."""
    return Cost(
        sum(cost.prompt_micros for cost in costs),
        sum(cost.completion_micros for cost in costs),
        sum(cost.cache_saved_micros for cost in costs),
        sum(cost.batch_saved_micros for cost in costs),
        sum(cost.adjustment_micros for cost in costs),
    )


def conserved(parent: Cost, children: tuple[Cost, ...]) -> bool:
    """Require parent net cost to equal child net sum plus parent adjustment."""
    child_total = sum(child.net_micros for child in children)
    return parent.net_micros == child_total + parent.adjustment_micros


def require_conserved(parent: Cost, children: tuple[Cost, ...]) -> None:
    if not conserved(parent, children):
        raise AttributionError(
            "cost conservation: children plus explicit adjustment differ from parent"
        )


def group_costs(records: tuple[tuple[str, Cost], ...]) -> dict[str, Cost]:
    """Roll up costs by task/session/tool/model label."""
    groups: dict[str, list[Cost]] = {}
    for label, cost in records:
        if not label:
            raise AttributionError("cost grouping: label must be non-empty")
        groups.setdefault(label, []).append(cost)
    return {label: add_costs(tuple(groups[label])) for label in sorted(groups)}


def from_rate_breakdown(breakdown: object, baseline_micros: int) -> Cost:
    """Translate the shared rate-card result without recomputing prices."""
    from frugent.ratecard import CostBreakdown

    if not isinstance(breakdown, CostBreakdown) or baseline_micros < breakdown.total_micros:
        raise AttributionError("rate breakdown: invalid object or baseline")
    cache_saved = baseline_micros - breakdown.gross_micros
    return Cost(
        breakdown.uncached_prompt_micros + breakdown.cached_prompt_micros + cache_saved,
        breakdown.completion_micros,
        cache_saved,
        breakdown.batch_discount_micros,
    )


def net_shares(costs: dict[str, Cost]) -> dict[str, float]:
    """Return quantized non-negative shares of total net cost."""
    if any(cost.net_micros < 0 for cost in costs.values()):
        raise AttributionError("cost shares: negative net cost")
    total = sum(cost.net_micros for cost in costs.values())
    if total == 0:
        return {label: 0.0 for label in sorted(costs)}
    return {label: round(costs[label].net_micros / total, 6) for label in sorted(costs)}
