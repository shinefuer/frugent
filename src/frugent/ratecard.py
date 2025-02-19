"""Fictional integer rate cards used by every synthetic cost computation."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from frugent.types import Usage

PPM = 1_000_000


class RateCardError(ValueError):
    """Raised when a fictional rate card is invalid."""


@dataclass(frozen=True, slots=True)
class ModelRate:
    """Fictional per-1000-token prices and multiplicative discounts in ppm."""

    model: str
    prompt_micros_per_1k: int
    completion_micros_per_1k: int
    cache_price_ppm: int = PPM
    batch_price_ppm: int = PPM

    def __post_init__(self) -> None:
        if not self.model:
            raise RateCardError("model rate: model must be non-empty")
        prices = (self.prompt_micros_per_1k, self.completion_micros_per_1k)
        discounts = (self.cache_price_ppm, self.batch_price_ppm)
        if any(
            isinstance(value, bool) or not isinstance(value, int) for value in prices + discounts
        ):
            raise RateCardError("model rate: prices and discounts must be integers")
        if any(value < 0 for value in prices):
            raise RateCardError("model rate: prices must be non-negative")
        if any(not 0 <= value <= PPM for value in discounts):
            raise RateCardError("model rate: discounts must be in [0, 1000000]")

    def to_record(self) -> dict[str, str | int]:
        return {
            "model": self.model,
            "prompt_micros_per_1k": self.prompt_micros_per_1k,
            "completion_micros_per_1k": self.completion_micros_per_1k,
            "cache_price_ppm": self.cache_price_ppm,
            "batch_price_ppm": self.batch_price_ppm,
        }

    @classmethod
    def from_record(cls, record: Mapping[str, Any]) -> ModelRate:
        expected = {
            "model",
            "prompt_micros_per_1k",
            "completion_micros_per_1k",
            "cache_price_ppm",
            "batch_price_ppm",
        }
        if set(record) != expected:
            raise RateCardError("model rate: unexpected record fields")
        return cls(**record)


@dataclass(frozen=True, slots=True)
class RateCard:
    """Named fictional rates with deterministic model lookup."""

    label: str
    rates: tuple[ModelRate, ...]
    schema_version: int = 1

    def __post_init__(self) -> None:
        if "fictional" not in self.label.casefold():
            raise RateCardError("rate card label must explicitly include 'fictional'")
        if self.schema_version != 1:
            raise RateCardError("rate card schema_version: expected 1")
        if not self.rates:
            raise RateCardError("rate card: expected at least one model")
        names = [rate.model for rate in self.rates]
        if names != sorted(names) or len(set(names)) != len(names):
            raise RateCardError("rate card: models must be unique and sorted")

    def model_rate(self, model: str) -> ModelRate:
        for rate in self.rates:
            if rate.model == model:
                return rate
        raise RateCardError(f"rate card: unknown model {model!r}")

    def to_record(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "label": self.label,
            "rates": [rate.to_record() for rate in self.rates],
        }

    @classmethod
    def from_record(cls, record: Mapping[str, Any]) -> RateCard:
        expected = {"schema_version", "label", "rates"}
        if set(record) != expected:
            raise RateCardError("rate card: unexpected record fields")
        raw_rates = record["rates"]
        if not isinstance(raw_rates, list):
            raise RateCardError("rate card.rates: expected a list")
        parsed: list[ModelRate] = []
        rate_fields = {
            "model",
            "prompt_micros_per_1k",
            "completion_micros_per_1k",
            "cache_price_ppm",
            "batch_price_ppm",
        }
        for index, item in enumerate(raw_rates):
            if not isinstance(item, Mapping) or set(item) != rate_fields:
                raise RateCardError(f"rate card.rates[{index}]: unexpected fields")
            parsed.append(ModelRate(**item))
        return cls(record["label"], tuple(parsed), record["schema_version"])


@dataclass(frozen=True, slots=True)
class CostBreakdown:
    """Integer micro-cost components whose total is exactly conserved."""

    uncached_prompt_micros: int
    cached_prompt_micros: int
    completion_micros: int
    batch_discount_micros: int = 0

    def __post_init__(self) -> None:
        values = (
            self.uncached_prompt_micros,
            self.cached_prompt_micros,
            self.completion_micros,
            self.batch_discount_micros,
        )
        if any(
            isinstance(value, bool) or not isinstance(value, int) or value < 0 for value in values
        ):
            raise RateCardError("cost breakdown: components must be non-negative integers")
        if self.batch_discount_micros > sum(values[:3]):
            raise RateCardError("cost breakdown: discount exceeds gross cost")

    @property
    def gross_micros(self) -> int:
        return self.uncached_prompt_micros + self.cached_prompt_micros + self.completion_micros

    @property
    def total_micros(self) -> int:
        return self.gross_micros - self.batch_discount_micros


def _ceil_div(numerator: int, denominator: int) -> int:
    return (numerator + denominator - 1) // denominator


def price_usage(rate: ModelRate, usage: Usage, *, batched: bool = False) -> CostBreakdown:
    """Price one measured usage with deterministic ceiling arithmetic."""
    uncached_tokens = usage.prompt_tokens - usage.cached_prompt_tokens
    uncached = _ceil_div(uncached_tokens * rate.prompt_micros_per_1k, 1000)
    cached_numerator = usage.cached_prompt_tokens * rate.prompt_micros_per_1k * rate.cache_price_ppm
    cached = _ceil_div(cached_numerator, 1000 * PPM)
    completion = _ceil_div(usage.completion_tokens * rate.completion_micros_per_1k, 1000)
    gross = uncached + cached + completion
    discount = 0 if not batched else gross - (gross * rate.batch_price_ppm // PPM)
    return CostBreakdown(uncached, cached, completion, discount)


@dataclass(frozen=True, slots=True)
class Savings:
    """Attribution against the same usage priced without optimizations."""

    baseline_micros: int
    actual_micros: int
    cache_saved_micros: int
    batch_saved_micros: int

    def __post_init__(self) -> None:
        values = (
            self.baseline_micros,
            self.actual_micros,
            self.cache_saved_micros,
            self.batch_saved_micros,
        )
        if any(
            isinstance(value, bool) or not isinstance(value, int) or value < 0 for value in values
        ):
            raise RateCardError("savings: components must be non-negative integers")
        if (
            self.baseline_micros - self.actual_micros
            != self.cache_saved_micros + self.batch_saved_micros
        ):
            raise RateCardError("savings: attribution does not conserve baseline difference")


def attribute_savings(rate: ModelRate, usage: Usage, *, batched: bool = False) -> Savings:
    baseline_usage = Usage(usage.prompt_tokens, usage.completion_tokens, 0)
    baseline = price_usage(rate, baseline_usage).total_micros
    cached_cost = price_usage(rate, usage).total_micros
    actual = price_usage(rate, usage, batched=batched).total_micros
    return Savings(baseline, actual, baseline - cached_cost, cached_cost - actual)


def rate_card_fingerprint(card: RateCard) -> str:
    """Fingerprint every fictional price and discount used by a run."""
    from frugent.codec import payload_digest

    return payload_digest(card.to_record())
