#!/usr/bin/env bash
set -euo pipefail
# Clean-machine verification for the Functionality rule.
# Offline: python tests, extension tests, .vsix packaging. No API key needed.

python3 -m venv .verify-venv
source .verify-venv/bin/activate
pip install -q -e ".[dev]"
pytest -q                                    # 53 offline tests

pushd vscode-extension >/dev/null
npm ci
npm run compile
npm test
npx @vscode/vsce package --out ../agent-harness-verify.vsix
popd >/dev/null

deactivate
echo "OK: python suite, extension suite, and .vsix packaging all green."
echo "Live check (needs OPENAI_API_KEY): agent-harness run demo_tests/"