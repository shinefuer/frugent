"""Command-line entry point."""

from __future__ import annotations

import argparse
from collections.abc import Sequence

from frugent import __version__


def build_parser() -> argparse.ArgumentParser:
    """Build the root command parser."""
    parser = argparse.ArgumentParser(prog="frugent", description="离线运行时机制工具包")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the command-line interface."""
    build_parser().parse_args(argv)
    return 0
