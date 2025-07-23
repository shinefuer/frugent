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


def route_trace(
    names: tuple[str, ...], requests: tuple[tuple[str, ...], ...], load_penalty_ppm: int = 0
) -> tuple[str, ...]:
    """Route a planted-affinity trace from empty instance caches."""
    if len(set(names)) != len(names) or not names:
        raise PromptRouterError("routing trace: unique instance names required")
    instances = tuple(Instance(name, PrefixTrie()) for name in names)
    return tuple(route_and_record(instances, request, load_penalty_ppm) for request in requests)


def seeded_instances(placements: dict[str, tuple[tuple[str, ...], ...]]) -> tuple[Instance, ...]:
    """Create a pool from explicit planted cache prefixes."""
    instances: list[Instance] = []
    for name in sorted(placements):
        trie = PrefixTrie()
        for sequence in placements[name]:
            trie.insert(sequence)
        instances.append(Instance(name, trie))
    if not instances:
        raise PromptRouterError("seeded pool: expected placements")
    return tuple(instances)


def routed_hit_tokens(
    instances: tuple[Instance, ...],
    assignments: tuple[str, ...],
    requests: tuple[tuple[str, ...], ...],
) -> int:
    """Measure matched tokens against a fixed pre-route cache snapshot."""
    if len(assignments) != len(requests):
        raise PromptRouterError("routing measurement: assignments and requests differ")
    by_name = {instance.name: instance for instance in instances}
    if any(name not in by_name for name in assignments):
        raise PromptRouterError("routing measurement: unknown instance")
    return sum(
        by_name[name].cache.longest_prefix(request)
        for name, request in zip(assignments, requests, strict=True)
    )
