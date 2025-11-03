"""Behavior and invariant tests."""

from __future__ import annotations

import pytest

import frugent.sandbox as m


def test_policy_accepts_explicit_offline_allowlist() -> None:
    policy = m.Policy(
        (("python", "-m", "pytest"), ("git", "diff")),
        ("src/**", "tests/**"),
        frozenset({"PYTHONHASHSEED"}),
    )
    assert policy.command_prefixes[0] == ("python", "-m", "pytest")


def test_policy_rejects_empty_command_prefix() -> None:
    with pytest.raises(m.SandboxError, match="command prefixes"):
        m.Policy(((),), (), frozenset())


def test_command_decision_matches_complete_prefix_tokens() -> None:
    policy = m.Policy((("git", "diff"),), (), frozenset())
    assert m.command_decision(policy, ("git", "diff", "--stat")).allowed
    assert not m.command_decision(policy, ("git", "status")).allowed
    assert not m.command_decision(policy, ("git-diff",)).allowed


@pytest.mark.parametrize(
    "argv",
    [
        ("sh", "-c", "echo ok; rm x"),
        ("echo", "$(touch x)"),
        ("cat", "x > y"),
        ("printf", "`id`"),
        ("cmd", "a||b"),
        ("cmd", "a&&b"),
    ],
)
def test_shell_injection_corpus_is_always_denied(argv: tuple[str, ...]) -> None:
    assert not m.injection_decision(argv).allowed


def test_literal_argv_without_shell_syntax_is_allowed() -> None:
    assert m.injection_decision(("python", "-m", "pytest", "tests/test_x.py::test_ok")).allowed


@pytest.mark.parametrize("path", ["../x", "src/../../x", "/etc/passwd", ""])
def test_path_decision_rejects_traversal_and_absolute_paths(path: str) -> None:
    policy = m.Policy((("read",),), ("src/**",), frozenset())
    assert not m.path_decision(policy, path).allowed


def test_path_decision_accepts_declared_relative_glob() -> None:
    policy = m.Policy((("read",),), ("src/**/*.py",), frozenset())
    assert m.path_decision(policy, "src/frugent/cache.py").allowed
    assert not m.path_decision(policy, "tests/test_cache.py").allowed


def test_environment_decision_reports_unknown_names() -> None:
    policy = m.Policy((("run",),), (), frozenset({"SAFE"}))
    decision = m.environment_decision(policy, {"SAFE": "1", "SECRET": "x"})
    assert not decision.allowed
    assert "SECRET" in decision.reason


def test_environment_decision_accepts_only_declared_values() -> None:
    policy = m.Policy((("run",),), (), frozenset({"SAFE"}))
    assert m.environment_decision(policy, {"SAFE": "1"}).allowed


@pytest.mark.parametrize(
    "path", ["..", "../a", "a/../b", "a/b/../../c", "/tmp/x", "//server/share", "src/../../../etc"]
)
def test_path_traversal_corpus_is_always_denied(path: str) -> None:
    policy = m.Policy((("read",),), ("**",), frozenset())
    assert not m.path_decision(policy, path).allowed


def test_combined_decision_returns_first_denial() -> None:
    policy = m.Policy((("python",),), ("src/**",), frozenset())
    assert "metacharacter" in m.decide(policy, ("python", "x;bad"), ("../x",)).reason
    assert "outside allowlist" in m.decide(policy, ("python", "safe"), ("tests/x",)).reason
    assert m.decide(policy, ("python", "safe"), ("src/x",)).allowed


def test_dry_run_record_contains_decision_without_output() -> None:
    policy = m.Policy((("echo",),), (), frozenset())
    record = m.dry_run_record(policy, ("echo", "safe"))
    assert record == {
        "schema_version": 1,
        "mode": "dry_run",
        "argv": ["echo", "safe"],
        "paths": [],
        "allowed": True,
        "reason": "all sandbox rules allowed",
        "rule": None,
    }
    assert "stdout" not in record


def test_same_policy_request_produces_identical_dry_run_record() -> None:
    policy = m.Policy((("python", "-m"),), ("src/**",), frozenset({"SAFE"}))
    args = (policy, ("python", "-m", "module"), ("src/x.py",), {"SAFE": "1"})
    assert m.dry_run_record(*args) == m.dry_run_record(*args)
