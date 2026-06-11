"""Behavior and invariant tests."""

from __future__ import annotations

import pytest

import frugent.semantic_cache as m


@pytest.mark.parametrize(
    ("left", "right"),
    [
        (" Fix  BUG ", "fix bug"),
        ("\uff21\uff22\uff23", "abc"),
        ("x\n\ty", "x y"),
        ("Straße", "STRASSE"),
    ],
)
def test_equivalent_text_normalizations_match(left: str, right: str) -> None:
    assert m.normalize_text(left) == m.normalize_text(right)


def test_case_sensitive_normalization_preserves_case() -> None:
    assert m.normalize_text(" A  B ", fold_case=False) == "A B"


def test_payload_canonicalizes_argument_order() -> None:
    left = m.normalized_payload("Fix X", "EDIT", {"b": 2, "a": 1})
    right = m.normalized_payload(" fix  x ", "edit", {"a": 1, "b": 2})
    assert left == right


def test_payload_keeps_tool_arguments_case_sensitive() -> None:
    assert m.normalized_payload("x", "tool", {"path": "A.py"}) != m.normalized_payload(
        "x", "tool", {"path": "a.py"}
    )


@pytest.mark.parametrize("spacing", [" ", "  ", "\n", "\t", " \n "])
def test_normalization_equivalence_always_hits_same_key(spacing: str) -> None:
    left = f"Fix{spacing}Cache"
    assert m.normalized_payload(left, "EDIT", {"path": "x.py"}) == m.normalized_payload(
        "fix cache", "edit", {"path": "x.py"}
    )


def test_exact_key_hits_equivalent_normalizations() -> None:
    assert m.exact_key(" Fix\nX ", "EDIT", {"line": 1}) == m.exact_key("fix x", "edit", {"line": 1})


@pytest.mark.parametrize(
    "change", [{"prompt": "fix y"}, {"tool_name": "read"}, {"arguments": {"line": 2}}]
)
def test_exact_key_changes_for_nonequivalent_payload(change: dict[str, object]) -> None:
    base = {"prompt": "fix x", "tool_name": "edit", "arguments": {"line": 1}}
    base.update(change)
    assert m.exact_key(**base) != m.exact_key("fix x", "edit", {"line": 1})  # type: ignore[arg-type]


def test_shingles_fold_equivalent_text() -> None:
    assert m.shingles(" Fix  Bug ") == m.shingles("fix bug")
    assert m.jaccard(m.shingles("abcdef"), m.shingles("abcxef")) == 0.142857


@pytest.mark.parametrize("width", [0, -1])
def test_shingles_require_positive_width(width: int) -> None:
    with pytest.raises(m.SemanticCacheError, match="width"):
        m.shingles("text", width)


def test_minhash_signature_is_seeded_and_repeatable() -> None:
    values = m.shingles("deterministic prompt")
    assert m.minhash_signature(values, seed=9) == m.minhash_signature(values, seed=9)
    assert m.minhash_signature(values, seed=9) != m.minhash_signature(values, seed=10)


def test_identical_signatures_have_unit_similarity() -> None:
    signature = m.minhash_signature(m.shingles("same"), permutations=8)
    assert m.minhash_similarity(signature, signature) == 1.0


@pytest.mark.parametrize(
    ("prompt", "tool", "arguments"),
    [
        ("fix y", "edit", {"path": "x.py"}),
        ("fix x", "read", {"path": "x.py"}),
        ("fix x", "edit", {"path": "y.py"}),
        ("fix x", "edit", {"path": "x.py", "line": 0}),
    ],
)
def test_nonequivalent_payload_is_never_served(
    prompt: str, tool: str, arguments: dict[str, object]
) -> None:
    original = m.exact_key("fix x", "edit", {"path": "x.py"})
    changed = m.exact_key(prompt, tool, arguments)
    assert changed != original


def test_exact_lookup_never_returns_nonequivalent_key() -> None:
    key = m.exact_key("fix x", "edit", {"line": 1})
    entry = m.SemanticEntry(key, b"result", 0)
    assert m.exact_lookup((entry,), key, 1, 10) == b"result"
    other = m.exact_key("fix y", "edit", {"line": 1})
    assert m.exact_lookup((entry,), other, 1, 10) is None


def test_exact_lookup_expires_at_ttl_boundary() -> None:
    entry = m.SemanticEntry("k", b"x", 5)
    assert m.exact_lookup((entry,), "k", 14, 10) == b"x"
    assert m.exact_lookup((entry,), "k", 15, 10) is None


def test_fuzzy_candidates_rank_but_do_not_return_responses() -> None:
    candidates = m.fuzzy_candidates(
        "fix cache bug", {"a": "fix cache bug", "b": "fix cache bugs", "x": "write docs"}, 0.4
    )
    assert candidates[0] == ("a", 1.0)
    assert all(isinstance(score, float) for _, score in candidates)


@pytest.mark.parametrize("threshold", [-0.1, 1.1, float("nan")])
def test_fuzzy_candidates_reject_invalid_threshold(threshold: float) -> None:
    with pytest.raises(m.SemanticCacheError, match="threshold"):
        m.fuzzy_candidates("q", {}, threshold)


@pytest.mark.parametrize("left", ["", "a", "abc", "longer phrase"])
@pytest.mark.parametrize("right", ["", "b", "abd", "longest phrase"])
def test_minhash_similarity_stays_in_unit_interval(left: str, right: str) -> None:
    first = m.minhash_signature(m.shingles(left), permutations=16, seed=3)
    second = m.minhash_signature(m.shingles(right), permutations=16, seed=3)
    assert 0.0 <= m.minhash_similarity(first, second) <= 1.0


def test_semantic_metrics_separate_requests_and_evictions() -> None:
    result = m.semantic_metrics(("hit", "miss", "eviction", "hit"))
    assert result == m.SemanticMetrics(2, 1, 1)
    assert result.hit_rate == 0.666667


def test_semantic_metrics_reject_unknown_outcome() -> None:
    with pytest.raises(m.SemanticCacheError, match="unknown outcome"):
        m.semantic_metrics(("collision",))


def test_semantic_policy_accepts_empty_bounded_cache() -> None:
    assert m.SemanticPolicy(0, 0).capacity == 0
    with pytest.raises(m.SemanticCacheError, match="limits"):
        m.SemanticPolicy(-1, 1)


def test_semantic_state_requires_unique_canonical_keys() -> None:
    entry = m.SemanticEntry("k", b"x", 0)
    with pytest.raises(m.SemanticCacheError, match="duplicate"):
        m.SemanticState((entry, entry))
    with pytest.raises(m.SemanticCacheError, match="key order"):
        m.SemanticState((m.SemanticEntry("z", b"", 0), entry))


def test_empty_semantic_state_has_zero_metrics() -> None:
    state = m.SemanticState()
    assert state.entries == ()
    assert m.semantic_metrics(state.outcomes) == m.SemanticMetrics(0, 0, 0)


def test_state_lookup_purges_expired_entries_before_exact_match() -> None:
    state = m.SemanticState((m.SemanticEntry("k", b"old", 0),))
    response, updated = m.state_lookup(state, "k", 10, m.SemanticPolicy(2, 10))
    assert response is None and updated.entries == ()
    assert updated.outcomes == ("miss",)


def test_state_put_replaces_exact_key_without_duplicate() -> None:
    policy = m.SemanticPolicy(2, 100)
    state = m.state_put(m.SemanticState(), m.SemanticEntry("k", b"one", 0), policy)
    updated = m.state_put(state, m.SemanticEntry("k", b"two", 1), policy)
    assert updated.entries == (m.SemanticEntry("k", b"two", 1),)
    assert updated.outcomes == ()


def test_state_eviction_is_oldest_then_lexical() -> None:
    policy = m.SemanticPolicy(2, 100)
    state = m.SemanticState()
    for entry in (
        m.SemanticEntry("b", b"b", 0),
        m.SemanticEntry("a", b"a", 0),
        m.SemanticEntry("c", b"c", 1),
    ):
        state = m.state_put(state, entry, policy)
    assert tuple(entry.key for entry in state.entries) == ("b", "c")
    assert m.state_metrics(state).evictions == 1


def test_state_metrics_count_only_lookups_as_requests() -> None:
    policy = m.SemanticPolicy(1, 100)
    state = m.state_put(m.SemanticState(), m.SemanticEntry("a", b"x", 0), policy)
    _, state = m.state_lookup(state, "a", 1, policy)
    _, state = m.state_lookup(state, "b", 2, policy)
    state = m.state_put(state, m.SemanticEntry("b", b"y", 2), policy)
    metrics = m.state_metrics(state)
    assert metrics.hits + metrics.misses == 2
    assert metrics.evictions == 1


def test_state_record_preserves_arbitrary_response_bytes() -> None:
    state = m.SemanticState((m.SemanticEntry("k", bytes(range(256)), 4),), ("hit",))
    record = m.state_record(state)
    assert record["schema_version"] == 1
    assert record["entries"][0]["response_hex"].endswith("ff")


def test_semantic_state_record_roundtrips_exactly() -> None:
    state = m.SemanticState((m.SemanticEntry("a", b"\x00\xff", 3),), ("miss", "hit"))
    assert m.state_from_record(m.state_record(state)) == state


def test_semantic_state_record_rejects_unknown_fields() -> None:
    record = m.state_record(m.SemanticState())
    record["extra"] = 1
    with pytest.raises(m.SemanticCacheError, match="schema"):
        m.state_from_record(record)


def test_semantic_state_record_does_not_drop_malformed_entries() -> None:
    record = {"schema_version": 1, "entries": ["not-an-object"], "outcomes": []}
    with pytest.raises(m.SemanticCacheError, match="entry type"):
        m.state_from_record(record)
