"""Fictional rate-card arithmetic and schema tests."""

from __future__ import annotations

import pytest

import frugent.ratecard as r


def test_model_rate_record_uses_explicit_fictional_units() -> None:
    rate = r.ModelRate("scripted-small", 120, 400, 250_000, 800_000)
    assert rate.to_record() == {
        "model": "scripted-small",
        "prompt_micros_per_1k": 120,
        "completion_micros_per_1k": 400,
        "cache_price_ppm": 250_000,
        "batch_price_ppm": 800_000,
    }


@pytest.mark.parametrize("field", ["prompt_micros_per_1k", "completion_micros_per_1k"])
def test_model_rate_rejects_negative_prices(field: str) -> None:
    values = {"model": "m", "prompt_micros_per_1k": 1, "completion_micros_per_1k": 1}
    values[field] = -1
    with pytest.raises(r.RateCardError, match="non-negative"):
        r.ModelRate(**values)
