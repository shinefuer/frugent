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


@pytest.mark.parametrize("discount", [0, 1, 500_000, 999_999, 1_000_000])
def test_model_rate_accepts_closed_discount_interval(discount: int) -> None:
    assert r.ModelRate("m", 1, 2, discount, discount).cache_price_ppm == discount


@pytest.mark.parametrize("discount", [-1, 1_000_001, True, 0.5])
def test_model_rate_rejects_ambiguous_discount(discount: object) -> None:
    with pytest.raises(r.RateCardError, match="discount"):
        r.ModelRate("m", 1, 2, discount, 1)  # type: ignore[arg-type]


def test_model_rate_requires_model_identity() -> None:
    with pytest.raises(r.RateCardError, match="model must be non-empty"):
        r.ModelRate("", 1, 2)


def test_rate_card_lookup_is_exact() -> None:
    card = r.RateCard(
        "demo fictional rates",
        (r.ModelRate("large", 10, 20), r.ModelRate("small", 2, 4)),
    )
    assert card.model_rate("small").completion_micros_per_1k == 4
    with pytest.raises(r.RateCardError, match="unknown model"):
        card.model_rate("Small")


def test_rate_card_requires_honest_label() -> None:
    with pytest.raises(r.RateCardError, match="fictional"):
        r.RateCard("provider pricing", (r.ModelRate("m", 1, 1),))


def test_rate_card_rejects_unsorted_models() -> None:
    with pytest.raises(r.RateCardError, match="unique and sorted"):
        r.RateCard("fictional", (r.ModelRate("z", 1, 1), r.ModelRate("a", 1, 1)))


def test_rate_card_rejects_duplicate_models() -> None:
    with pytest.raises(r.RateCardError, match="unique and sorted"):
        r.RateCard("fictional", (r.ModelRate("m", 1, 1), r.ModelRate("m", 2, 2)))


def test_rate_card_wire_shape_is_stable() -> None:
    card = r.RateCard("offline fictional v1", (r.ModelRate("tiny", 3, 7, 500_000),))
    assert card.to_record() == {
        "schema_version": 1,
        "label": "offline fictional v1",
        "rates": [
            {
                "model": "tiny",
                "prompt_micros_per_1k": 3,
                "completion_micros_per_1k": 7,
                "cache_price_ppm": 500_000,
                "batch_price_ppm": 1_000_000,
            }
        ],
    }


def test_rate_card_record_roundtrip() -> None:
    original = r.RateCard(
        "synthetic fictional",
        (r.ModelRate("large", 5, 12), r.ModelRate("small", 1, 3, 200_000, 900_000)),
    )
    assert r.RateCard.from_record(original.to_record()) == original


@pytest.mark.parametrize("rates", [None, {}, "rates", 1])
def test_rate_card_parser_requires_rate_list(rates: object) -> None:
    with pytest.raises(r.RateCardError, match="expected a list"):
        r.RateCard.from_record({"schema_version": 1, "label": "fictional", "rates": rates})
