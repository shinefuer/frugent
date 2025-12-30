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
