"""Fictional rate-card arithmetic and schema tests."""

from __future__ import annotations

import pytest

import frugent.ratecard as r
from frugent.types import Usage


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


def test_cost_breakdown_conserves_components() -> None:
    cost = r.CostBreakdown(10, 2, 8, 5)
    assert cost.gross_micros == 20
    assert cost.total_micros == 15


def test_cost_breakdown_rejects_excess_discount() -> None:
    with pytest.raises(r.RateCardError, match="exceeds gross"):
        r.CostBreakdown(1, 1, 1, 4)


def test_price_usage_separates_cache_and_batch_effects() -> None:
    rate = r.ModelRate("m", 1_000, 2_000, 250_000, 750_000)
    usage = Usage(prompt_tokens=100, completion_tokens=10, cached_prompt_tokens=40)
    cost = r.price_usage(rate, usage, batched=True)
    assert cost.uncached_prompt_micros == 60
    assert cost.cached_prompt_micros == 10
    assert cost.completion_micros == 20
    assert cost.batch_discount_micros == 23
    assert cost.total_micros == 67


def test_price_usage_rounds_positive_fraction_up() -> None:
    assert r.price_usage(r.ModelRate("m", 1, 1), Usage(1, 0)).total_micros == 1


@pytest.mark.parametrize("prompt", [0, 1, 10, 999, 1000, 1001, 4096])
def test_prompt_cost_never_decreases_with_tokens(prompt: int) -> None:
    rate = r.ModelRate("m", 137, 211)
    current = r.price_usage(rate, Usage(prompt, 0)).total_micros
    following = r.price_usage(rate, Usage(prompt + 1, 0)).total_micros
    assert following >= current


@pytest.mark.parametrize("cached", [0, 1, 10, 500, 1000])
def test_more_discounted_cache_never_increases_cost(cached: int) -> None:
    rate = r.ModelRate("m", 1000, 1000, 100_000)
    current = r.price_usage(rate, Usage(1000, 0, cached)).total_micros
    following = r.price_usage(rate, Usage(1000, 0, min(1000, cached + 1))).total_micros
    assert following <= current


def test_savings_attribution_reconciles_to_baseline() -> None:
    rate = r.ModelRate("m", 1000, 2000, 250_000, 800_000)
    savings = r.attribute_savings(rate, Usage(100, 20, 80), batched=True)
    assert savings.baseline_micros - savings.actual_micros == (
        savings.cache_saved_micros + savings.batch_saved_micros
    )
    assert savings.cache_saved_micros > 0
    assert savings.batch_saved_micros > 0


def test_unoptimized_usage_reports_zero_savings() -> None:
    savings = r.attribute_savings(r.ModelRate("m", 2, 3), Usage(4, 5))
    assert savings.cache_saved_micros == 0
    assert savings.batch_saved_micros == 0
