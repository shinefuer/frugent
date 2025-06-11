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
