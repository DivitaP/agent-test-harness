"""Stable entry point for VS Code when the project is not installed globally.

Configure ``agentHarness.command`` to invoke this file with a Python runtime.
The extension appends normal CLI arguments (``run <suite> --json``).
"""

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC = PROJECT_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from agent_harness.cli import main  # noqa: E402 - path setup must happen first


if __name__ == "__main__":
    raise SystemExit(main())
