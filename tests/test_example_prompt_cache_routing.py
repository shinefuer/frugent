"""Executable prompt-cache routing example."""

from pathlib import Path

from examples.prompt_cache_routing.example import run

EXAMPLE_PATH = Path(__file__).parents[1] / "examples" / "prompt_cache_routing" / "example.py"
EXPECTED_ARTIFACT = "routing.svg"


def test_example_recovers_exhaustive_fixed_snapshot_optimum(tmp_path: Path) -> None:
    destination = tmp_path / EXPECTED_ARTIFACT
    result = run(destination)
    assert result["greedy"] == result["optimum"]
    assert result["hit_tokens"] == 9
    assert 0 < result["token_savings"] < 1


def test_routing_svg_contains_both_measured_policies(tmp_path: Path) -> None:
    destination = tmp_path / EXPECTED_ARTIFACT
    run(destination)
    svg = destination.read_text()
    assert svg.startswith("<svg") and svg.endswith("</svg>")
    assert "no-cache" in svg and "prefix-route" in svg
