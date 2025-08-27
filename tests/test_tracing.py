"""Behavior and invariant tests."""

from __future__ import annotations

import pytest

import frugent.tracing as m


def test_span_duration_uses_half_open_timestamps() -> None:
    span = m.Span("s", "route", 10, 17, attributes=(("model", "small"),))
    assert span.duration_us == 7


@pytest.mark.parametrize(
    "values", [("", "n", 0, 0), ("s", "", 0, 0), ("s", "n", -1, 0), ("s", "n", 2, 1)]
)
def test_span_rejects_invalid_identity_or_timing(values: tuple[object, ...]) -> None:
    with pytest.raises(m.TraceError, match="span"):
        m.Span(*values)  # type: ignore[arg-type]


def test_validate_forest_accepts_nested_timings() -> None:
    spans = (m.Span("root", "run", 0, 10), m.Span("child", "route", 2, 8, "root"))
    assert m.validate_forest(spans) is None


def test_validate_forest_rejects_child_outside_parent() -> None:
    with pytest.raises(m.TraceError, match="outside parent"):
        m.validate_forest((m.Span("p", "p", 0, 5), m.Span("c", "c", 4, 6, "p")))


def test_span_forest_rejects_missing_parent() -> None:
    with pytest.raises(m.TraceError, match="missing parent"):
        m.validate_forest((m.Span("c", "c", 0, 1, "missing"),))


def test_span_forest_rejects_parent_cycle() -> None:
    spans = (m.Span("a", "a", 0, 2, "b"), m.Span("b", "b", 0, 2, "a"))
    with pytest.raises(m.TraceError, match="cycle"):
        m.validate_forest(spans)


def test_child_index_sorts_roots_and_siblings() -> None:
    spans = (
        m.Span("b", "b", 2, 3),
        m.Span("root", "r", 0, 9),
        m.Span("a", "a", 1, 2, "root"),
        m.Span("c", "c", 1, 3, "root"),
    )
    index = m.child_index(spans)
    assert tuple(span.span_id for span in index[None]) == ("root", "b")
    assert tuple(span.span_id for span in index["root"]) == ("a", "c")


def test_preorder_places_parent_before_descendants() -> None:
    spans = (m.Span("g", "g", 2, 3, "c"), m.Span("c", "c", 1, 5, "r"), m.Span("r", "r", 0, 6))
    assert tuple(span.span_id for span in m.preorder(spans)) == ("r", "c", "g")


def test_exclusive_duration_subtracts_direct_children_only() -> None:
    spans = (m.Span("r", "r", 0, 10), m.Span("a", "a", 1, 4, "r"), m.Span("b", "b", 6, 9, "r"))
    assert m.exclusive_duration(spans[0], spans) == 4


def test_exclusive_duration_rejects_overlapping_siblings() -> None:
    spans = (m.Span("r", "r", 0, 10), m.Span("a", "a", 1, 6, "r"), m.Span("b", "b", 5, 9, "r"))
    with pytest.raises(m.TraceError, match="overlap"):
        m.exclusive_duration(spans[0], spans)


def test_root_duration_partitions_into_exclusive_and_children() -> None:
    spans = (m.Span("r", "r", 0, 20), m.Span("a", "a", 1, 5, "r"), m.Span("b", "b", 8, 15, "r"))
    root = spans[0]
    child_total = sum(span.duration_us for span in spans[1:])
    assert m.exclusive_duration(root, spans) + child_total == root.duration_us


def test_span_id_is_repeatable_and_sequence_sensitive() -> None:
    assert m.span_id(7, 2, "route") == m.span_id(7, 2, "route")
    assert m.span_id(7, 2, "route") != m.span_id(7, 3, "route")
    assert len(m.span_id(7, 2, "route")) == 16


def test_span_record_golden_roundtrip() -> None:
    span = m.Span("s", "tool", 1, 4, "p", (("tool", "read"),))
    assert m.span_record(span) == {
        "span_id": "s",
        "parent_id": "p",
        "name": "tool",
        "start_us": 1,
        "end_us": 4,
        "attributes": {"tool": "read"},
    }
    assert m.span_from_record(m.span_record(span)) == span


@pytest.mark.parametrize("sequence", range(12))
def test_span_roundtrip_preserves_deterministic_ids(sequence: int) -> None:
    identifier = m.span_id(9, sequence, f"step-{sequence}")
    span = m.Span(
        identifier, "step", sequence, sequence + 1, attributes=(("sequence", str(sequence)),)
    )
    assert m.span_from_record(m.span_record(span)) == span
