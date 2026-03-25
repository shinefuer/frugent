"""Compare a runtime cascade policy with the exhaustive planted optimum."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from frugent.cascade_dp import (
    Action,
    DifficultyMixture,
    Policy,
    evaluate,
    optimal_policy,
    optimum_gap,
)


def run(destination: Path) -> dict[str, object]:
    mixture = DifficultyMixture((0.5, 0.3, 0.2))
    options = (
        (Action("small", 10, 0.90), Action("large", 30, 0.99)),
        (Action("small", 10, 0.70), Action("large", 30, 0.95)),
        (Action("small", 10, 0.35), Action("large", 30, 0.90)),
    )
    optimum = optimal_policy(options, mixture, 0.82)
    runtime = Policy(optimum.actions)
    cost, quality = evaluate(runtime, mixture)
    result = {
        "synthetic": True,
        "fictional_rate_card": True,
        "models": list(runtime.models),
        "expected_cost_micros": cost,
        "scripted_quality": quality,
        "optimum_gap_micros": optimum_gap(runtime, options, mixture, 0.82),
    }
    destination.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n")
    return result


def main() -> None:
    destination = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("cascade-optimum.json")
    result = run(destination)
    print(
        f"synthetic cascade: models={result['models']} optimum_gap={result['optimum_gap_micros']}"
    )


if __name__ == "__main__":
    main()
