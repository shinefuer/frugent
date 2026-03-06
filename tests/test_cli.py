"""CLI behavior over offline synthetic inputs."""

from __future__ import annotations

import frugent.cli as m


def test_empty_cli_remains_a_successful_library_probe() -> None:
    assert m.main([]) == 0


def test_command_output_keeps_artifacts_optional() -> None:
    assert m.CommandOutput({"ok": True}).artifact is None
