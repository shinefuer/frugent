"""CLI behavior over offline synthetic inputs."""

from __future__ import annotations

import json

import frugent.cli as m


def test_empty_cli_remains_a_successful_library_probe() -> None:
    assert m.main([]) == 0


def test_command_output_keeps_artifacts_optional() -> None:
    assert m.CommandOutput({"ok": True}).artifact is None


def test_route_command_reports_planted_prefix_hits(capsys: object) -> None:
    assert m.main(["route"]) == 0
    output = json.loads(capsys.readouterr().out)
    assert output == {"assignments": ["left", "right"], "cached_tokens": 4, "synthetic": True}
