"""Deterministic offline token accounting protocols and implementations."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

TOKEN_PATTERN = re.compile(r"[A-Za-z_][A-Za-z_0-9]*|[0-9]+|[^\w\s]", re.UNICODE)


class TokenizerError(ValueError):
    """Raised when token accounting input or configuration is invalid."""


@runtime_checkable
class Tokenizer(Protocol):
    """Minimal deterministic tokenizer used by budget mechanisms."""

    def encode(self, text: str) -> tuple[str, ...]: ...

    def count(self, text: str) -> int: ...


@dataclass(frozen=True, slots=True)
class HeuristicTokenizer:
    """Stable lexical counter; it does not imitate a provider tokenizer."""

    lowercase: bool = False
    seed: int = 0

    def __post_init__(self) -> None:
        if isinstance(self.seed, bool) or not isinstance(self.seed, int) or self.seed < 0:
            raise TokenizerError("tokenizer.seed: expected a non-negative integer")

    def encode(self, text: str) -> tuple[str, ...]:
        if not isinstance(text, str):
            raise TokenizerError("tokenizer input: expected text")
        normalized = text.casefold() if self.lowercase else text
        return tuple(TOKEN_PATTERN.findall(normalized))

    def count(self, text: str) -> int:
        return len(self.encode(text))


def render_message(role: str, content: str) -> str:
    """Render a message without allowing delimiter injection through roles."""
    if role not in {"system", "user", "assistant", "tool"}:
        raise TokenizerError(f"prompt role: unsupported {role!r}")
    if not isinstance(content, str):
        raise TokenizerError("prompt content: expected text")
    return f"<{role}>\n{content}\n</{role}>"


def render_prompt(messages: tuple[tuple[str, str], ...]) -> str:
    """Render an ordered prompt with a single stable separator."""
    return "\n".join(render_message(role, content) for role, content in messages)


def count_prompt_by_role(
    messages: tuple[tuple[str, str], ...], tokenizer: Tokenizer
) -> dict[str, int]:
    """Count rendered message tokens per role using the supplied tokenizer."""
    totals = {"system": 0, "user": 0, "assistant": 0, "tool": 0}
    for role, content in messages:
        rendered = render_message(role, content)
        totals[role] += tokenizer.count(rendered)
    return totals


def token_offsets(text: str, *, lowercase: bool = False) -> tuple[tuple[str, int, int], ...]:
    """Return token text and half-open source offsets for highlighting."""
    if lowercase:
        raise TokenizerError("token offsets: lowercase mode would lose source fidelity")
    return tuple(
        (match.group(0), match.start(), match.end()) for match in TOKEN_PATTERN.finditer(text)
    )


def truncate_tokens(text: str, limit: int) -> str:
    """Return the longest source prefix containing no more than limit tokens."""
    if isinstance(limit, bool) or not isinstance(limit, int) or limit < 0:
        raise TokenizerError("truncate limit: expected a non-negative integer")
    offsets = token_offsets(text)
    if len(offsets) <= limit:
        return text
    if limit == 0:
        return ""
    return text[: offsets[limit - 1][2]]
