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


def markdown_table(rows: tuple[MetricRow, ...]) -> str:
    if not rows:
        raise ReportError("markdown table: expected rows")
    lines = [
        "| policy | completed | tokens | fictional cost (micros) | P50 ms | P95 ms |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
        policy = row.policy.replace("|", "\\|").replace("\n", " ")
        lines.append(
            f"| {policy} | {row.completed} | {row.tokens} | {row.cost_micros} | "
            f"{row.p50_ms:.3f} | {row.p95_ms:.3f} |"
        )
    return "\n".join(lines)


def markdown_report(
    metadata: RunMetadata, rows: tuple[MetricRow, ...], limitations: tuple[str, ...]
) -> str:
    if not limitations or any(not item for item in limitations):
        raise ReportError("report: at least one limitation is required")
    meta = metadata_record(metadata)
    lines = [
        "# Frugent synthetic cost report",
        "",
        "本报告仅使用 planted synthetic workload 与 fictional rate card。",
        "",
        "## Run metadata",
        "",
    ]
    lines.extend(f"- {key}: `{value}`" for key, value in meta.items())
    lines.extend(("", "## Measured comparison", "", markdown_table(rows), "", "## Limitations", ""))
    lines.extend(f"- {item}" for item in limitations)
    return "\n".join(lines) + "\n"


def html_report(
    metadata: RunMetadata, rows: tuple[MetricRow, ...], limitations: tuple[str, ...]
) -> str:
    import html

    if not limitations:
        raise ReportError("html report: limitations are required")
    cells = "".join(
        "<tr>"
        + "".join(
            f"<td>{html.escape(str(value))}</td>"
            for value in (
                row.policy,
                row.completed,
                row.tokens,
                row.cost_micros,
                row.p50_ms,
                row.p95_ms,
            )
        )
        + "</tr>"
        for row in rows
    )
    limits = "".join(f"<li>{html.escape(item)}</li>" for item in limitations)
    metadata_html = "".join(
        f"<dt>{html.escape(key)}</dt><dd>{html.escape(str(value))}</dd>"
        for key, value in metadata_record(metadata).items()
    )
    chart = svg_bars(rows, field="cost_micros", title="Fictional cost by policy")
    return (
        '<!doctype html><html><head><meta charset="utf-8">'
        "<title>Frugent synthetic report</title>"
        "<style>body{font-family:sans-serif;max-width:900px;margin:auto}"
        "td,th{padding:.4rem}</style></head><body>"
        "<h1>Frugent synthetic cost report</h1>"
        "<p>Offline synthetic measurements; fictional rate card.</p>"
        f"<dl>{metadata_html}</dl>{chart}<table><tbody>{cells}</tbody></table>"
        f"<h2>Limitations</h2><ul>{limits}</ul></body></html>"
    )
