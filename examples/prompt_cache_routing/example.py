"""Route a planted-affinity trace and emit a measured token SVG."""

from __future__ import annotations

import sys
from pathlib import Path

from frugent.prefix import PrefixTrie
from frugent.prompt_router import (
    Instance,
    exhaustive_assignment,
    greedy_fixed_assignment,
    routed_hit_tokens,
)
from frugent.reports import MetricRow, svg_bars


def run(destination: Path) -> dict[str, object]:
    left, right = PrefixTrie(), PrefixTrie()
    left.insert(("repo:a", "policy", "src"))
    right.insert(("repo:b", "policy", "tests"))
    instances = (Instance("left", left), Instance("right", right))
    requests = (
        ("repo:a", "policy", "src", "edit"),
        ("repo:b", "policy", "tests", "fix"),
        ("repo:a", "policy", "src", "docs"),
    )
    greedy = greedy_fixed_assignment(instances, requests)
    optimum = exhaustive_assignment(instances, requests)
    hit_tokens = routed_hit_tokens(instances, greedy, requests)
    total_tokens = sum(map(len, requests))
    rows = (
        MetricRow("no-cache", 3, total_tokens, total_tokens, 1, 1),
        MetricRow("prefix-route", 3, total_tokens - hit_tokens, total_tokens - hit_tokens, 1, 1),
    )
    destination.write_text(svg_bars(rows, field="tokens", title="Synthetic prompt tokens"))
    return {
        "synthetic": True,
        "greedy": greedy,
        "optimum": optimum,
        "hit_tokens": hit_tokens,
        "token_savings": round(hit_tokens / total_tokens, 6),
    }


def main() -> None:
    destination = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("prompt-cache-routing.svg")
    result = run(destination)
    print(
        "synthetic prompt routing: "
        f"hit_tokens={result['hit_tokens']} savings={result['token_savings']}"
    )


if __name__ == "__main__":
    main()
