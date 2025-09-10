"""Versioned checksummed JSONL trace persistence and migration."""

from __future__ import annotations

from dataclasses import dataclass


class TraceIOError(ValueError):
    """Raised for corrupted or unsupported trace streams."""


@dataclass(frozen=True, slots=True)
class TraceHeader:
    run_id: str
    seed: int
    config_hash: str
    rate_card_hash: str
    schema_version: int = 2

    def __post_init__(self) -> None:
        if (
            not self.run_id
            or self.seed < 0
            or not self.config_hash
            or not self.rate_card_hash
            or self.schema_version != 2
        ):
            raise TraceIOError("trace header: invalid field")

    def to_record(self) -> dict[str, object]:
        return {
            "run_id": self.run_id,
            "seed": self.seed,
            "config_hash": self.config_hash,
            "rate_card_hash": self.rate_card_hash,
            "schema_version": self.schema_version,
        }
