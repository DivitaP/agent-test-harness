#!/usr/bin/env bash
# Create a dedicated demo environment without modifying an existing .venv.
set -euo pipefail

project_dir="$(cd "$(dirname "$0")/.." && pwd)"
python_bin="${PYTHON_BIN:-python3}"
demo_venv="$project_dir/.demo-venv"

"$python_bin" -m venv "$demo_venv"
"$demo_venv/bin/python" -m pip install --upgrade pip
"$demo_venv/bin/python" -m pip install -e "$project_dir[dev,demo]"

printf '\nReady. Run the Support Desk suite with:\n'
printf '  %s/scripts/run_harness.sh run examples/support_desk/support_tests/\n' "$project_dir"
