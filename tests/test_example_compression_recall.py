"""Executable compression recall example."""

from pathlib import Path

from examples.compression_recall.example import run

EXAMPLE_PATH = Path(__file__).parents[1] / "examples" / "compression_recall" / "example.py"
EXPECTED_ARTIFACT = "recall.svg"


def test_example_recall_degrades_monotonically_with_smaller_budgets(tmp_path: Path) -> None:
    curve = run(tmp_path / EXPECTED_ARTIFACT)["curve"]
    recalls = [recall for _, recall in curve]
    assert recalls == sorted(recalls)
    assert recalls[0] == 0 and recalls[-1] == 1
