"""Prefix trie affinity, lifecycle, and serialization tests."""

from __future__ import annotations

import frugent.prefix as p


def test_longest_prefix_counts_shared_tokens() -> None:
    trie = p.PrefixTrie()
    trie.insert(("system", "rules", "user", "task-a"))
    trie.insert(("system", "rules", "user", "task-b"))
    assert trie.longest_prefix(("system", "rules", "user", "task-c")) == 3
    assert trie.longest_prefix(("other",)) == 0
    assert trie.sequence_count == 2


def test_duplicate_insert_tracks_frequency() -> None:
    trie = p.PrefixTrie()
    trie.insert(("a", "b"))
    trie.insert(("a", "b"))
    assert trie.sequence_count == 2
    assert trie.longest_prefix(("a", "b", "c")) == 2
