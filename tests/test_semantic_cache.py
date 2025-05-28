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
