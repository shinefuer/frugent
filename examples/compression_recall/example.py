"""Measure planted-needle recall over increasing context budgets."""

from __future__ import annotations

import sys
from pathlib import Path

from frugent.compression import Block, recall_curve


def run(destination: Path) -> dict[str, object]:
    blocks = tuple(
        Block(
            f"m{index}",
            f"message {index}" + (" needle constraint" if index in {2, 5, 8} else ""),
            2 + index % 3,
            index,
            planted_relevance=20 if index in {2, 5, 8} else 1,
        )
        for index in range(10)
    )
    curve = recall_curve(blocks, frozenset({"m2", "m5", "m8"}), (0, 4, 8, 12, 20, 32))
    width, height = 520, 180
    points = " ".join(f"{20 + budget * 14},{150 - recall * 120:.1f}" for budget, recall in curve)
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" role="img">'
        "<title>Synthetic planted-needle recall</title>"
        f'<polyline points="{points}" fill="none" stroke="#3973ac"/></svg>'
    )
    destination.write_text(svg)
    return {"synthetic": True, "curve": curve}


def main() -> None:
    destination = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("compression-recall.svg")
    result = run(destination)
    print(f"synthetic compression: curve={result['curve']}")


if __name__ == "__main__":
    main()
