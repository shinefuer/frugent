"""Bootstrap contract tests."""

from __future__ import annotations

import subprocess
import sys
import tomllib
from pathlib import Path

import frugent
from frugent.cli import build_parser, main


def test_version_has_three_numeric_parts() -> None:
    assert len(frugent.__version__.split(".")) == 3
    assert all(part.isdigit() for part in frugent.__version__.split("."))


def test_version_matches_installed_metadata_and_changelog() -> None:
    root = Path(__file__).parents[1]
    project = tomllib.loads((root / "pyproject.toml").read_text())
    assert project["project"]["dynamic"] == ["version"]
    version_path = project["tool"]["hatch"]["version"]["path"]
    assert version_path == "src/frugent/_version.py"
    assert f'__version__ = "{frugent.__version__}"' in (root / version_path).read_text()
    headings = [
        line.removeprefix("## ").split(" - ", 1)[0]
        for line in (root / "CHANGELOG.md").read_text().splitlines()
        if line.startswith("## ")
    ]
    assert headings[0] == frugent.__version__


def test_root_parser_uses_public_program_name() -> None:
    assert build_parser().prog == "frugent"


def test_cli_accepts_no_arguments() -> None:
    assert main([]) == 0


def test_module_import_is_silent() -> None:
    result = subprocess.run(
        [sys.executable, "-c", "import frugent"],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert result.stdout == ""
    assert result.stderr == ""
