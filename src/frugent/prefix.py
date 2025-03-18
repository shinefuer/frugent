"""Prefix sequence index for prompt-cache affinity analysis."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


class PrefixError(ValueError):
    """Raised when prefix-index operations are invalid."""


def _validated_tokens(value: Any) -> tuple[str, ...]:
    if not isinstance(value, tuple) or not all(isinstance(token, str) and token for token in value):
        raise PrefixError("prefix tokens: expected a tuple of non-empty strings")
    return value


@dataclass(slots=True)
class _Node:
    children: dict[str, _Node] = field(default_factory=dict)
    terminal_count: int = 0
    visit_count: int = 0


@dataclass(slots=True)
class PrefixTrie:
    """A deterministic trie over already-rendered prompt token strings."""

    _root: _Node = field(default_factory=_Node)
    sequence_count: int = 0

    def insert(self, tokens: tuple[str, ...]) -> None:
        tokens = _validated_tokens(tokens)
        node = self._root
        node.visit_count += 1
        for token in tokens:
            node = node.children.setdefault(token, _Node())
            node.visit_count += 1
        node.terminal_count += 1
        self.sequence_count += 1

    def longest_prefix(self, tokens: tuple[str, ...]) -> int:
        node = self._root
        matched = 0
        for token in tokens:
            child = node.children.get(token)
            if child is None:
                break
            node = child
            matched += 1
        return matched
