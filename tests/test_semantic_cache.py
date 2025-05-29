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
