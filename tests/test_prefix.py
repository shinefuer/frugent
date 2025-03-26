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


@pytest.mark.parametrize("prefix", [("x",), ("a", "x"), ("a", "b", "x")])
def test_missing_prefix_frequency_is_zero(prefix: tuple[str, ...]) -> None:
    trie = p.PrefixTrie()
    trie.insert(("a", "b"))
    assert p.prefix_frequency(trie, prefix) == 0
    assert p.exact_frequency(trie, prefix) == 0


def test_root_frequency_equals_inserted_sequence_count() -> None:
    trie = p.PrefixTrie()
    for index in range(7):
        trie.insert((str(index),))
    assert p.prefix_frequency(trie, ()) == trie.sequence_count == 7


def test_remove_decrements_one_duplicate_at_a_time() -> None:
    trie = p.PrefixTrie()
    trie.insert(("a", "b"))
    trie.insert(("a", "b"))
    assert p.remove(trie, ("a", "b")) is True
    assert p.exact_frequency(trie, ("a", "b")) == 1
    assert p.remove(trie, ("a", "b")) is True
    assert trie.longest_prefix(("a", "b")) == 0
    assert p.remove(trie, ("a", "b")) is False


def test_remove_prunes_only_unused_branch() -> None:
    trie = p.PrefixTrie()
    trie.insert(("root", "left"))
    trie.insert(("root", "right"))
    assert p.remove(trie, ("root", "left"))
    assert trie.longest_prefix(("root", "left")) == 1
    assert trie.longest_prefix(("root", "right")) == 2
    assert p.prefix_frequency(trie, ("root",)) == 1


def test_remove_rejects_nonterminal_prefix() -> None:
    trie = p.PrefixTrie()
    trie.insert(("a", "b"))
    assert p.remove(trie, ("a",)) is False
    assert trie.sequence_count == 1


def test_candidate_ranking_prefers_length_then_frequency() -> None:
    left, right = p.PrefixTrie(), p.PrefixTrie()
    left.insert(("a", "b"))
    right.insert(("a", "b", "c"))
    assert p.rank_candidates({"left": left, "right": right}, ("a", "b", "c", "d"))[0][:2] == (
        "right",
        3,
    )
    left.insert(("a", "b", "c"))
    left.insert(("a", "b", "c"))
    assert p.rank_candidates({"left": left, "right": right}, ("a", "b", "c"))[0][0] == "left"


def test_prefix_record_roundtrip_preserves_multiplicity() -> None:
    trie = p.PrefixTrie()
    for sequence in (("z",), ("a", "b"), ("a", "b"), ()):
        trie.insert(sequence)
    record = p.trie_to_record(trie)
    assert record == {"schema_version": 1, "sequences": [[], ["a", "b"], ["a", "b"], ["z"]]}
    restored = p.trie_from_record(record)
    assert p.trie_to_record(restored) == record


@pytest.mark.parametrize(
    "record",
    [
        {},
        {"schema_version": 2, "sequences": []},
        {"schema_version": 1, "sequences": {}},
        {"schema_version": 1, "sequences": ["abc"]},
        {"schema_version": 1, "sequences": [["a", ""]]},
    ],
)
def test_prefix_record_rejects_malformed_shapes(record: dict[str, object]) -> None:
    with pytest.raises(p.PrefixError, match="prefix"):
        p.trie_from_record(record)
