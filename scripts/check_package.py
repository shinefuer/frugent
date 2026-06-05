"""Install the built wheel into a temporary venv and smoke-test import plus CLI."""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path


def run(command: list[str]) -> None:
    subprocess.run(command, check=True, capture_output=True, text=True)


def main() -> int:
    wheels = sorted(Path("dist").glob("frugent-*.whl"))
    if len(wheels) != 1:
        raise RuntimeError(f"expected exactly one frugent wheel, found {len(wheels)}")
    with tempfile.TemporaryDirectory(prefix="frugent-wheel-") as directory:
        root = Path(directory)
        run([sys.executable, "-m", "venv", str(root)])
        python = root / "bin" / "python"
        run([str(python), "-m", "pip", "install", "--no-deps", str(wheels[0].resolve())])
        run([str(python), "-c", "import frugent; assert frugent.__version__"])
        run([str(root / "bin" / "frugent"), "--help"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
