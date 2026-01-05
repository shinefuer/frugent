"""Behavior and invariant tests."""

from __future__ import annotations

import pytest

import frugent.reports as m


def test_metadata_record_names_reproducibility_inputs() -> None:
    metadata = m.RunMetadata("0.1.0", 7, "cfg", "rates")
    assert m.metadata_record(metadata) == {
        "version": "0.1.0",
        "seed": 7,
        "config_hash": "cfg",
        "rate_card_fingerprint": "rates",
    }


def test_metric_row_preserves_measured_counts() -> None:
    row = m.MetricRow("candidate", 3, 120, 44, 5.5, 9.0)
    assert (row.tokens, row.p95_ms) == (120, 9.0)
    with pytest.raises(m.ReportError, match="metric row"):
        m.MetricRow("bad", 1, 2, 3, 9.0, 8.0)


@pytest.mark.parametrize("field", ["", "latency", "p95_ms"])
def test_svg_rejects_undefined_measurements(field: str) -> None:
    row = m.MetricRow("x", 1, 2, 3, 4, 5)
    with pytest.raises(m.ReportError, match="svg"):
        m.svg_bars((row,), field=field, title="x")


def test_svg_bars_is_deterministic_and_escapes_labels() -> None:
    rows = (
        m.MetricRow("<base>", 1, 20, 9, 1, 2),
        m.MetricRow("stack", 2, 10, 4, 1, 2),
    )
    first = m.svg_bars(rows, field="tokens", title="tokens & cost")
    assert first == m.svg_bars(rows, field="tokens", title="tokens & cost")
    assert "&lt;base&gt;" in first and "tokens &amp; cost" in first
    assert "<base>" not in first


def test_markdown_table_has_explicit_fictional_cost_units() -> None:
    text = m.markdown_table((m.MetricRow("a|b", 1, 2, 3, 4, 5),))
    assert "fictional cost (micros)" in text
    assert "a\\|b" in text
    assert text.count("\n") == 2


def test_markdown_report_discloses_synthetic_scope() -> None:
    metadata = m.RunMetadata("v", 1, "cfg", "rate")
    report = m.markdown_report(metadata, (m.MetricRow("x", 1, 2, 3, 4, 5),), ("offline only",))
    assert "planted synthetic workload" in report
    assert "fictional rate card" in report
    assert "offline only" in report
