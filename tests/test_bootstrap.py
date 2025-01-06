"""Bootstrap contract tests."""

from __future__ import annotations

import subprocess
import sys

import frugent
from frugent.cli import build_parser, main


def test_version_has_three_numeric_parts() -> None:
    assert len(frugent.__version__.split(".")) == 3
    assert all(part.isdigit() for part in frugent.__version__.split("."))


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
