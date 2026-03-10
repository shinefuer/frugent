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


def test_cache_command_replays_hits_in_request_order(capsys: object) -> None:
    assert m.main(["cache"]) == 0
    output = json.loads(capsys.readouterr().out)
    assert output["requests"] == 3 and output["hits"] == 1
    assert output["cached_tokens"] == 8


def test_initial_command_help_names_measured_operations() -> None:
    help_text = m.build_parser().format_help()
    assert "cache" in help_text and "route" in help_text
    assert "offline" not in help_text.casefold() or "离线" in help_text


def test_compress_command_emits_monotone_recall(capsys: object) -> None:
    assert m.main(["compress", "--token-budget", "4096"]) == 0
    curve = json.loads(capsys.readouterr().out)["curve"]
    assert [point[0] for point in curve] == sorted(point[0] for point in curve)
    assert [point[1] for point in curve] == sorted(point[1] for point in curve)
