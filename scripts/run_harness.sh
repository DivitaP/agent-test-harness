#!/usr/bin/env bash
# Stable VS Code/terminal launcher for the project-local demo environment.
set -euo pipefail

project_dir="$(cd "$(dirname "$0")/.." && pwd)"
demo_python="$project_dir/.demo-venv/bin/python"

if [[ ! -x "$demo_python" ]]; then
  echo "Demo environment not found. Run: bash scripts/bootstrap_demo.sh" >&2
  exit 2
fi

exec "$demo_python" "$project_dir/scripts/run_harness.py" "$@"
