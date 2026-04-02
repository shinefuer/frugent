"""Run the complete offline pipeline and write its self-contained HTML report."""

from __future__ import annotations

import sys
from pathlib import Path

from frugent.pipeline import PipelineConfig, run_pipeline
from frugent.trace_io import trace_fingerprint


def run(destination: Path) -> dict[str, object]:
    artifacts = run_pipeline(PipelineConfig(seed=42, tasks=12))
    destination.write_text(artifacts.html)
    comparison = artifacts.comparison
    return {
        "synthetic": True,
        "fictional_rate_card": True,
        "completed": comparison.stack.completed,
        "token_savings": comparison.token_savings,
        "cost_savings_micros": comparison.cost_savings_micros,
        "trace_fingerprint": trace_fingerprint(artifacts.trace),
    }


def main() -> None:
    destination = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("mini-cost-audit.html")
    result = run(destination)
    print(
        "synthetic cost audit: "
        f"completed={result['completed']} "
        f"savings={result['cost_savings_micros']} fictional micros"
    )


if __name__ == "__main__":
    main()
