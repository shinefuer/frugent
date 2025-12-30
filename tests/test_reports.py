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
