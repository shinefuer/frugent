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
