"""Sandboxed argv execution and deterministic scripted tool replay."""

from __future__ import annotations

from dataclasses import dataclass


class ToolError(RuntimeError):
    """Raised for invalid, denied, or failed tool execution."""


@dataclass(frozen=True, slots=True)
class ToolCall:
    call_id: str
    argv: tuple[str, ...]
    paths: tuple[str, ...] = ()
    environment: tuple[tuple[str, str], ...] = ()

    def __post_init__(self) -> None:
        if not self.call_id or not self.argv or any(not arg for arg in self.argv):
            raise ToolError("tool call: identity and argv must be non-empty")
        if tuple(sorted(self.environment)) != self.environment:
            raise ToolError("tool call: environment must be sorted")


@dataclass(frozen=True, slots=True)
class ToolResult:
    call_id: str
    exit_code: int
    stdout: bytes
    stderr: bytes
    timed_out: bool = False
    cancelled: bool = False

    def __post_init__(self) -> None:
        if (
            not self.call_id
            or isinstance(self.exit_code, bool)
            or not isinstance(self.exit_code, int)
        ):
            raise ToolError("tool result: invalid identity or exit code")
        if self.timed_out and self.cancelled:
            raise ToolError("tool result: cannot be both timed out and cancelled")


class ScriptedTools:
    """Consume planted results in call order without external execution."""

    def __init__(self, scripts: tuple[tuple[ToolCall, ToolResult], ...]) -> None:
        self._scripts = scripts
        self._cursor = 0

    def execute(self, call: ToolCall) -> ToolResult:
        if self._cursor >= len(self._scripts):
            raise ToolError("scripted tools: no result remains")
        expected, result = self._scripts[self._cursor]
        if expected != call or result.call_id != call.call_id:
            raise ToolError("scripted tools: call does not match replay")
        self._cursor += 1
        return result

    @property
    def complete(self) -> bool:
        return self._cursor == len(self._scripts)


def dry_run(call: ToolCall, policy: object) -> ToolResult:
    """Return a decision trace without spawning a process."""
    from frugent.codec import canonical_json
    from frugent.sandbox import Policy, dry_run_record

    if not isinstance(policy, Policy):
        raise ToolError("tool dry run: expected sandbox policy")
    record = dry_run_record(policy, call.argv, call.paths, dict(call.environment))
    exit_code = 0 if record["allowed"] else 126
    return ToolResult(call.call_id, exit_code, canonical_json(record), b"")


def execute(call: ToolCall, policy: object, *, cwd: str, timeout_s: float = 5.0) -> ToolResult:
    """Execute an allowed argv vector without a shell and capture bytes."""
    import subprocess

    from frugent.sandbox import Policy, decide

    if not isinstance(policy, Policy) or timeout_s <= 0:
        raise ToolError("tool execute: invalid policy or timeout")
    decision = decide(policy, call.argv, call.paths, dict(call.environment))
    if not decision.allowed:
        return ToolResult(call.call_id, 126, b"", decision.reason.encode())
    try:
        completed = subprocess.run(
            call.argv,
            cwd=cwd,
            env=dict(call.environment),
            capture_output=True,
            timeout=timeout_s,
            check=False,
            shell=False,
        )
    except subprocess.TimeoutExpired as error:
        stdout = error.stdout or b""
        stderr = error.stderr or b""
        return ToolResult(call.call_id, 124, stdout, stderr, timed_out=True)
    except OSError as error:
        return ToolResult(call.call_id, 127, b"", str(error).encode())
    return ToolResult(call.call_id, completed.returncode, completed.stdout, completed.stderr)


def timeout_result(
    call_id: str, partial_stdout: bytes = b"", partial_stderr: bytes = b""
) -> ToolResult:
    """Construct a canonical timeout result for adapters and tests."""
    return ToolResult(call_id, 124, partial_stdout, partial_stderr, timed_out=True)


def cancelled_result(
    call_id: str, partial_stdout: bytes = b"", partial_stderr: bytes = b""
) -> ToolResult:
    """Construct a canonical cancellation result distinct from timeout."""
    return ToolResult(call_id, 130, partial_stdout, partial_stderr, cancelled=True)


def result_record(result: ToolResult) -> dict[str, object]:
    """Use hex so arbitrary bytes roundtrip through canonical JSON."""
    return {
        "schema_version": 1,
        "call_id": result.call_id,
        "exit_code": result.exit_code,
        "stdout_hex": result.stdout.hex(),
        "stderr_hex": result.stderr.hex(),
        "timed_out": result.timed_out,
        "cancelled": result.cancelled,
    }


def result_from_record(record: dict[str, object]) -> ToolResult:
    try:
        if record["schema_version"] != 1:
            raise ToolError("tool result record: unsupported schema")
        call_id, exit_code = record["call_id"], record["exit_code"]
        timed_out, cancelled = record["timed_out"], record["cancelled"]
        if (
            not isinstance(call_id, str)
            or not isinstance(exit_code, int)
            or isinstance(exit_code, bool)
        ):
            raise ToolError("tool result record: invalid identity or exit code")
        if not isinstance(timed_out, bool) or not isinstance(cancelled, bool):
            raise ToolError("tool result record: terminal flags must be booleans")
        return ToolResult(
            call_id,
            exit_code,
            bytes.fromhex(str(record["stdout_hex"])),
            bytes.fromhex(str(record["stderr_hex"])),
            timed_out,
            cancelled,
        )
    except (KeyError, ValueError) as error:
        raise ToolError(f"tool result record: invalid shape: {error}") from error
