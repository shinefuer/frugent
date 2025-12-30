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


def svg_bars(rows: tuple[MetricRow, ...], *, field: str, title: str) -> str:
    """Render one non-negative integer metric without plotting dependencies."""
    import html

    if not rows or field not in {"completed", "tokens", "cost_micros"}:
        raise ReportError("svg: unsupported or empty series")
    values = [int(getattr(row, field)) for row in rows]
    scale = max(values) or 1
    parts = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="640" '
        f'height="{60 + 36 * len(rows)}" role="img">',
        f"<title>{html.escape(title)}</title>",
    ]
    for index, (row, value) in enumerate(zip(rows, values, strict=True)):
        y = 36 + index * 36
        width = round(420 * value / scale)
        parts.append(f'<text x="8" y="{y + 16}">{html.escape(row.policy)}</text>')
        parts.append(f'<rect x="160" y="{y}" width="{width}" height="20" fill="#3973ac"/>')
        parts.append(f'<text x="{170 + width}" y="{y + 16}">{value}</text>')
    parts.append("</svg>")
    return "".join(parts)
