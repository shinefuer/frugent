"""Canonical codecs for deterministic persisted artifacts."""

from __future__ import annotations

import hashlib
import json
import math
from typing import Any


class CodecError(ValueError):
    """Raised when a payload cannot be represented canonically."""


def _reject_non_finite(value: Any, path: str = "$") -> None:
    if isinstance(value, float) and not math.isfinite(value):
        raise CodecError(f"{path}: non-finite float is not canonical")
    if isinstance(value, dict):
        for key, child in value.items():
            if not isinstance(key, str):
                raise CodecError(f"{path}: object keys must be strings")
            _reject_non_finite(child, f"{path}.{key}")
    elif isinstance(value, (list, tuple)):
        for index, child in enumerate(value):
            _reject_non_finite(child, f"{path}[{index}]")


def canonical_json(value: Any) -> bytes:
    """Encode JSON with stable ordering and no insignificant whitespace."""
    _reject_non_finite(value)
    try:
        rendered = json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
    except (TypeError, ValueError) as error:
        raise CodecError(f"payload is not JSON-compatible: {error}") from error
    return rendered.encode("utf-8")


def payload_digest(value: Any) -> str:
    """Return a namespaced SHA-256 digest of the canonical bytes."""
    return "sha256:" + hashlib.sha256(canonical_json(value)).hexdigest()
