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
