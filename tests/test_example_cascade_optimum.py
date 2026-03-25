"""Executable cascade policy example."""

from pathlib import Path

from examples.cascade_optimum.example import run

EXAMPLE_PATH = Path(__file__).parents[1] / "examples" / "cascade_optimum" / "example.py"
EXPECTED_ARTIFACT = "cascade.json"


def test_example_runtime_policy_matches_planted_optimum(tmp_path: Path) -> None:
    result = run(tmp_path / EXPECTED_ARTIFACT)
    assert result["optimum_gap_micros"] == 0
    assert result["scripted_quality"] >= 0.82
    assert result["fictional_rate_card"] is True
