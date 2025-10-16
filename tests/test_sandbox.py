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
