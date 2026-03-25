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


def test_cascade_artifact_is_stable_sorted_JSON(tmp_path: Path) -> None:
    import json

    destination = tmp_path / EXPECTED_ARTIFACT
    first = run(destination)
    encoded = destination.read_text()
    assert json.loads(encoded) == first
    assert encoded.index('"expected_cost_micros"') < encoded.index('"models"')
