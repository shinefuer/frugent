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


def test_script_entry_point_writes_artifact(tmp_path: Path) -> None:
    import subprocess
    import sys

    destination = tmp_path / EXPECTED_ARTIFACT
    result = subprocess.run(
        [sys.executable, str(EXAMPLE_PATH), str(destination)],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert destination.exists() and destination.stat().st_size > 40
    assert "synthetic" in result.stdout.casefold()
