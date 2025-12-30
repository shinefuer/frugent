"""Deterministic Markdown, HTML, and SVG reports from measured synthetic runs."""

from __future__ import annotations

from dataclasses import dataclass


class ReportError(ValueError):
    """Raised for malformed report inputs."""


@dataclass(frozen=True, slots=True)
class RunMetadata:
    version: str
    seed: int
    config_hash: str
    rate_card_fingerprint: str

    def __post_init__(self) -> None:
        if (
            not self.version
            or self.seed < 0
            or not self.config_hash
            or not self.rate_card_fingerprint
        ):
            raise ReportError("metadata: version, seed, and fingerprints are required")


def metadata_record(metadata: RunMetadata) -> dict[str, object]:
    return {
        "version": metadata.version,
        "seed": metadata.seed,
        "config_hash": metadata.config_hash,
        "rate_card_fingerprint": metadata.rate_card_fingerprint,
    }


@dataclass(frozen=True, slots=True)
class MetricRow:
    policy: str
    completed: int
    tokens: int
    cost_micros: int
    p50_ms: float
    p95_ms: float

    def __post_init__(self) -> None:
        values = (self.completed, self.tokens, self.cost_micros, self.p50_ms, self.p95_ms)
        if not self.policy or any(value < 0 for value in values) or self.p95_ms < self.p50_ms:
            raise ReportError("metric row: invalid policy, counts, costs, or percentiles")
