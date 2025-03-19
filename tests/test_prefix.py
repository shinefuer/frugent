"""Prefix trie affinity, lifecycle, and serialization tests."""

from __future__ import annotations

import pytest

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


@pytest.mark.parametrize("tokens", [("",), ("a", ""), ("a", 1), (None,)])
def test_prefix_insert_rejects_empty_or_non_string_tokens(tokens: tuple[object, ...]) -> None:
    with pytest.raises(p.PrefixError, match="prefix tokens"):
        p.PrefixTrie().insert(tokens)  # type: ignore[arg-type]


def test_empty_sequence_is_a_valid_root_terminal() -> None:
    trie = p.PrefixTrie()
    trie.insert(())
    assert trie.sequence_count == 1
    assert trie.longest_prefix(()) == 0


@pytest.mark.parametrize(
    ("sequence", "expected"),
    [((), 1.0), (("a",), 1.0), (("a", "b"), 0.5), (("x", "b"), 0.0)],
)
def test_prefix_coverage_quantifies_matched_request_fraction(
    sequence: tuple[str, ...], expected: float
) -> None:
    trie = p.PrefixTrie()
    trie.insert(("a", "c"))
    assert p.prefix_coverage(trie, sequence) == expected


def test_prefix_frequency_distinguishes_shared_and_exact_counts() -> None:
    trie = p.PrefixTrie()
    for sequence in (("a", "b"), ("a", "c"), ("a", "b")):
        trie.insert(sequence)
    assert p.prefix_frequency(trie, ("a",)) == 3
    assert p.prefix_frequency(trie, ("a", "b")) == 2
    assert p.exact_frequency(trie, ("a", "b")) == 2
    assert p.exact_frequency(trie, ("a",)) == 0
