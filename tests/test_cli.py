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


def test_batch_command_counts_single_flights(capsys: object) -> None:
    assert m.main(["batch"]) == 0
    output = json.loads(capsys.readouterr().out)
    assert output == {"batches": 2, "dedup_ratio": 0.333333, "executions": 2, "requests": 3}


def test_budget_command_never_allocates_beyond_limits(capsys: object) -> None:
    assert m.main(["budget", "--tasks", "5", "--token-budget", "33", "--cost-budget", "47"]) == 0
    output = json.loads(capsys.readouterr().out)
    assert output["allocated_tokens"] == 33
    assert output["allocated_cost_micros"] == 47


def test_commands_return_useful_error_codes_for_invalid_limits(capsys: object) -> None:
    assert m.main(["budget", "--tasks", "-1"]) == 2
    assert "frugent:" in capsys.readouterr().err
    assert m.main(["compress", "--token-budget", "-1"]) == 2


def test_trace_command_reports_verified_stream_metadata(capsys: object) -> None:
    assert m.main(["trace", "--seed", "6", "--tasks", "3"]) == 0
    output = json.loads(capsys.readouterr().out)
    assert output["run_id"] == "synthetic-6" and output["events"] == 2
    assert output["fingerprint"].startswith("sha256:")


def test_bench_command_labels_measured_scope(capsys: object) -> None:
    assert m.main(["bench", "--seed", "1", "--tasks", "8"]) == 0
    output = json.loads(capsys.readouterr().out)
    assert output["synthetic"] is True and output["fictional_rate_card"] is True
    assert output["completed"] == 8 and output["cost_savings_micros"] > 0


def test_report_command_writes_requested_self_contained_artifact(tmp_path: object) -> None:
    from pathlib import Path

    destination = Path(tmp_path) / "report.html"
    assert m.main(["report", "--format", "html", "--tasks", "4", "--output", str(destination)]) == 0
    assert destination.read_text().startswith("<!doctype html>")
    assert "fictional rate card" in destination.read_text()


def test_report_stdout_is_the_requested_artifact(capsys: object) -> None:
    assert m.main(["report", "--format", "markdown", "--tasks", "3"]) == 0
    assert capsys.readouterr().out.startswith("# Frugent synthetic cost report")
