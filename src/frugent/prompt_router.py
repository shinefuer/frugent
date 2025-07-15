"""Prefix-aware routing across deterministic cache-instance pools."""

from __future__ import annotations

from dataclasses import dataclass

from frugent.prefix import PrefixTrie


class PromptRouterError(ValueError):
    """Raised for invalid instance pools or traces."""


@dataclass(slots=True)
class Instance:
    name: str
    cache: PrefixTrie
    queued_tokens: int = 0

    def __post_init__(self) -> None:
        if not self.name or self.queued_tokens < 0:
            raise PromptRouterError("router instance: invalid name or queue")


def affinity_score(instance: Instance, tokens: tuple[str, ...], load_penalty_ppm: int = 0) -> int:
    """Score matched tokens in ppm units minus queued-token penalty."""
    if not 0 <= load_penalty_ppm <= 1_000_000:
        raise PromptRouterError("affinity score: load penalty must be ppm")
    matched = instance.cache.longest_prefix(tokens)
    return matched * 1_000_000 - instance.queued_tokens * load_penalty_ppm


def choose_instance(
    instances: tuple[Instance, ...], tokens: tuple[str, ...], load_penalty_ppm: int = 0
) -> Instance:
    if not instances or len({instance.name for instance in instances}) != len(instances):
        raise PromptRouterError("router pool: expected unique nonempty instances")
    return min(
        instances,
        key=lambda instance: (-affinity_score(instance, tokens, load_penalty_ppm), instance.name),
    )


def route_and_record(
    instances: tuple[Instance, ...], tokens: tuple[str, ...], load_penalty_ppm: int = 0
) -> str:
    """Choose one instance, record the complete prefix, and return its name."""
    selected = choose_instance(instances, tokens, load_penalty_ppm)
    selected.cache.insert(tokens)
    return selected.name
