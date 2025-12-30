"""Behavior and invariant tests."""

from __future__ import annotations

import frugent.reports as m


def test_metadata_record_names_reproducibility_inputs() -> None:
    metadata = m.RunMetadata("0.1.0", 7, "cfg", "rates")
    assert m.metadata_record(metadata) == {
        "version": "0.1.0",
        "seed": 7,
        "config_hash": "cfg",
        "rate_card_fingerprint": "rates",
    }
