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


@pytest.mark.parametrize(
    ("budget", "keys"), [(0, ()), (2, ("c",)), (4, ("b", "c")), (9, ("a", "b", "c"))]
)
def test_sliding_window_keeps_newest_contiguous_suffix(budget: int, keys: tuple[str, ...]) -> None:
    blocks = (m.Block("a", "a", 5, 0), m.Block("b", "b", 2, 1), m.Block("c", "c", 2, 2))
    assert tuple(block.key for block in m.sliding_window(blocks, budget)) == keys


@pytest.mark.parametrize("budget", range(0, 20))
def test_sliding_window_never_exceeds_budget(budget: int) -> None:
    blocks = tuple(m.Block(str(index), "x", index % 4 + 1, index) for index in range(10))
    selected = m.sliding_window(blocks, budget)
    assert sum(block.tokens for block in selected) <= budget
    assert blocks[-len(selected) :] == selected if selected else True


def test_extractive_summary_prefers_planted_fact_signal() -> None:
    blocks = (m.Block("old", "needle: port 7", 4, 0), m.Block("new", "chat", 2, 10))
    assert m.extractive_summary(blocks, 1) == (blocks[0],)


def test_extractive_summary_preserves_conversation_order() -> None:
    blocks = tuple(
        m.Block(str(index), "needle" if index != 1 else "plain", 1, index) for index in range(3)
    )
    assert tuple(block.key for block in m.extractive_summary(blocks, 2)) == ("0", "2")


def test_exact_budget_select_finds_planted_relevance_optimum() -> None:
    blocks = (
        m.Block("big", "x", 6, 0, planted_relevance=9),
        m.Block("a", "x", 5, 0, planted_relevance=8),
        m.Block("b", "x", 5, 0, planted_relevance=8),
    )
    assert tuple(block.key for block in m.exact_budget_select(blocks, 10)) == ("a", "b")


@pytest.mark.parametrize(
    ("selected", "needles", "expected"),
    [
        ((), frozenset(), 1.0),
        ((), frozenset({"a"}), 0.0),
        ((m.Block("a", "x", 1, 0),), frozenset({"a", "b"}), 0.5),
    ],
)
def test_needle_recall_uses_planted_key_ground_truth(
    selected: tuple[m.Block, ...], needles: frozenset[str], expected: float
) -> None:
    assert m.needle_recall(selected, needles) == expected


@pytest.mark.parametrize("budget", range(0, 16))
def test_exact_compression_never_exceeds_budget(budget: int) -> None:
    blocks = tuple(
        m.Block(str(index), "needle", index + 1, index, planted_relevance=9 - index)
        for index in range(7)
    )
    selected = m.exact_budget_select(blocks, budget)
    assert sum(block.tokens for block in selected) <= budget


def test_recall_curve_degrades_monotonically_with_less_budget() -> None:
    blocks = tuple(
        m.Block(str(index), "needle", index + 1, index, planted_relevance=10) for index in range(4)
    )
    curve = m.recall_curve(blocks, frozenset({"0", "1", "2", "3"}), tuple(range(11)))
    recalls = tuple(value for _, value in curve)
    assert all(recalls[index] <= recalls[index + 1] for index in range(len(recalls) - 1))


def test_scripted_summary_passes_ordered_text() -> None:
    blocks = (m.Block("a", "first", 1, 0), m.Block("b", "second", 1, 1))
    assert m.scripted_summary(blocks, lambda texts: " | ".join(texts)) == "first | second"


def test_scripted_summary_rejects_non_text_result() -> None:
    with pytest.raises(m.CompressionError, match="string result"):
        m.scripted_summary((), lambda _: 1)


def test_recall_curve_is_repeatable_for_same_planted_corpus() -> None:
    blocks = tuple(
        m.Block(str(index), f"fact {index}", 2, index, planted_relevance=index)
        for index in range(8)
    )
    args = (blocks, frozenset({"1", "3", "7"}), tuple(range(0, 17, 2)))
    assert m.recall_curve(*args) == m.recall_curve(*args)


def test_render_blocks_is_stable_and_single_line_per_block() -> None:
    blocks = (m.Block("a", "line1\nline2", 2, 0), m.Block("b", "done", 1, 1))
    assert m.render_blocks(blocks) == "[a] line1 line2\n[b] done"
    assert m.render_blocks(()) == ""
