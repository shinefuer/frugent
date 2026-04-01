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


def test_compression_svg_has_one_point_per_budget(tmp_path: Path) -> None:
    destination = tmp_path / EXPECTED_ARTIFACT
    result = run(destination)
    svg = destination.read_text()
    points = svg.split('points="', 1)[1].split('"', 1)[0].split()
    assert len(points) == len(result["curve"])
    assert "planted-needle recall" in svg
