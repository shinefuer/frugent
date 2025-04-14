"""Exact and greedy token-budget selection for context blocks."""

from __future__ import annotations

from dataclasses import dataclass


class KnapsackError(ValueError):
    """Raised for malformed items or capacities."""


@dataclass(frozen=True, slots=True)
class Item:
    key: str
    tokens: int
    value: int

    def __post_init__(self) -> None:
        if not self.key or isinstance(self.tokens, bool) or self.tokens <= 0 or self.value < 0:
            raise KnapsackError("item: key must be non-empty, tokens positive, value non-negative")


def exact_select(items: tuple[Item, ...], capacity: int) -> tuple[Item, ...]:
    """Maximize integer value with deterministic lexical tie-breaking."""
    if isinstance(capacity, bool) or not isinstance(capacity, int) or capacity < 0:
        raise KnapsackError("capacity: expected non-negative integer")
    states: dict[int, tuple[int, tuple[str, ...]]] = {0: (0, ())}
    by_key = {item.key: item for item in items}
    if len(by_key) != len(items):
        raise KnapsackError("items: keys must be unique")
    for item in sorted(items, key=lambda candidate: candidate.key):
        updated = dict(states)
        for weight, (value, keys) in states.items():
            new_weight = weight + item.tokens
            candidate = (value + item.value, (*keys, item.key))
            current = updated.get(new_weight)
            if new_weight <= capacity and (
                current is None or (-candidate[0], candidate[1]) < (-current[0], current[1])
            ):
                updated[new_weight] = candidate
        states = updated
    _, keys = min(states.values(), key=lambda state: (-state[0], state[1]))
    return tuple(by_key[key] for key in keys)


def greedy_select(items: tuple[Item, ...], capacity: int) -> tuple[Item, ...]:
    """Select by value density, absolute value, then lexical key."""
    if capacity < 0:
        raise KnapsackError("capacity: expected non-negative integer")
    ordered = sorted(items, key=lambda item: (-item.value / item.tokens, -item.value, item.key))
    selected: list[Item] = []
    remaining = capacity
    for item in ordered:
        if item.tokens <= remaining:
            selected.append(item)
            remaining -= item.tokens
    return tuple(sorted(selected, key=lambda item: item.key))


def selection_totals(items: tuple[Item, ...]) -> tuple[int, int]:
    """Return selected token weight and planted relevance value."""
    return sum(item.tokens for item in items), sum(item.value for item in items)
