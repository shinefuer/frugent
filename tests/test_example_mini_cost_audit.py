"""Executable full mini audit example."""

from pathlib import Path

from examples.mini_cost_audit.example import run

EXAMPLE_PATH = Path(__file__).parents[1] / "examples" / "mini_cost_audit" / "example.py"
EXPECTED_ARTIFACT = "audit.html"


def test_example_executes_full_measured_audit(tmp_path: Path) -> None:
    destination = tmp_path / EXPECTED_ARTIFACT
    result = run(destination)
    assert result["completed"] == 12
    assert result["token_savings"] > 0 and result["cost_savings_micros"] > 0
    assert result["trace_fingerprint"].startswith("sha256:")


def test_mini_audit_html_discloses_evidence_limits(tmp_path: Path) -> None:
    destination = tmp_path / EXPECTED_ARTIFACT
    result = run(destination)
    html = destination.read_text()
    assert result["fictional_rate_card"] is True and result["synthetic"] is True
    assert "fictional rate card" in html
    assert "No real model endpoint was called." in html
