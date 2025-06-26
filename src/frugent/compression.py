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


def block_score(block: Block, keywords: tuple[str, ...] = ("needle", "constraint", "error")) -> int:
    """Combine recency, tool density, and planted-fact keyword signals."""
    lowered = block.text.casefold()
    keyword_hits = sum(keyword.casefold() in lowered for keyword in keywords)
    return (
        block.recency
        + block.tool_density_ppm // 100_000
        + keyword_hits * 20
        + block.planted_relevance
    )


def extractive_summary(blocks: tuple[Block, ...], count: int) -> tuple[Block, ...]:
    if count < 0:
        raise CompressionError("extractive summary: count must be non-negative")
    selected = sorted(blocks, key=lambda block: (-block_score(block), block.key))[:count]
    keys = {block.key for block in selected}
    return tuple(block for block in blocks if block.key in keys)


def exact_budget_select(blocks: tuple[Block, ...], token_budget: int) -> tuple[Block, ...]:
    """Use planted relevance as knapsack value for synthetic recall checks."""
    from frugent.knapsack import Item, exact_select

    chosen = exact_select(
        tuple(Item(block.key, block.tokens, block.planted_relevance) for block in blocks),
        token_budget,
    )
    keys = {item.key for item in chosen}
    return tuple(block for block in blocks if block.key in keys)
