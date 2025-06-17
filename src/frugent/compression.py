"""Deterministic context compression and planted-needle recall."""

from __future__ import annotations

from dataclasses import dataclass


class CompressionError(ValueError):
    """Raised for invalid compression budgets or blocks."""


@dataclass(frozen=True, slots=True)
class Block:
    key: str
    text: str
    tokens: int
    recency: int
    tool_density_ppm: int = 0
    planted_relevance: int = 0

    def __post_init__(self) -> None:
        if (
            not self.key
            or self.tokens <= 0
            or self.recency < 0
            or not 0 <= self.tool_density_ppm <= 1_000_000
            or self.planted_relevance < 0
        ):
            raise CompressionError("compression block: invalid field")


def sliding_window(blocks: tuple[Block, ...], token_budget: int) -> tuple[Block, ...]:
    """Keep the newest suffix that fits the token budget."""
    if token_budget < 0:
        raise CompressionError("sliding window: budget must be non-negative")
    selected: list[Block] = []
    remaining = token_budget
    for block in reversed(blocks):
        if block.tokens > remaining:
            break
        selected.append(block)
        remaining -= block.tokens
    return tuple(reversed(selected))
