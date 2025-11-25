"""Offline scripted, replay, and local-loopback model adapter protocols."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


class AdapterError(RuntimeError):
    """Raised for invalid adapter requests or replay mismatches."""


@dataclass(frozen=True, slots=True)
class AdapterRequest:
    request_id: str
    prompt: bytes
    seed: int

    def __post_init__(self) -> None:
        if not self.request_id or self.seed < 0:
            raise AdapterError("adapter request: invalid id or seed")


@dataclass(frozen=True, slots=True)
class AdapterResponse:
    request_id: str
    content: bytes
    model: str
    prompt_tokens: int
    completion_tokens: int


@runtime_checkable
class Adapter(Protocol):
    def complete(self, request: AdapterRequest) -> AdapterResponse: ...
