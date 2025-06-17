"""Behavior and invariant tests."""

from __future__ import annotations

import pytest

import frugent.compression as m


def test_block_keeps_explicit_synthetic_relevance() -> None:
    block = m.Block("b", "needle", 3, 7, 500_000, 10)
    assert block.planted_relevance == 10


@pytest.mark.parametrize("values", [("", "x", 1, 0), ("x", "x", 0, 0), ("x", "x", 1, -1)])
def test_block_rejects_invalid_identity_weight_or_recency(values: tuple[object, ...]) -> None:
    with pytest.raises(m.CompressionError, match="block"):
        m.Block(*values)  # type: ignore[arg-type]
