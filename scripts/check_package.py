"""Smoke-check the import and console entry point in the active environment."""

from __future__ import annotations

import shutil

import frugent


def main() -> int:
    assert frugent.__version__
    assert shutil.which("frugent") is not None
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
