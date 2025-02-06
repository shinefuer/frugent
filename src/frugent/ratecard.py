"""Fictional integer rate cards used by every synthetic cost computation."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

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
