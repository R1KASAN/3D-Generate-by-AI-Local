"""Run the browser mock gate through the checked-in Playwright orchestration."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parents[2]
    environment = os.environ.copy()
    environment["GENERATION_ADAPTER"] = "mock"
    command = ["npm", "--prefix", str(root / "apps/web"), "run", "test:e2e"]
    return subprocess.run(command, cwd=root, env=environment, check=False).returncode


if __name__ == "__main__":
    raise SystemExit(main())
