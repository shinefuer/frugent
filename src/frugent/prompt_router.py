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
