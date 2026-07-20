# Agent Harness for VS Code

Semantic testing for LangGraph agents in the native Test Explorer. Each test
expands into three scorer results (process, evidence, output), so failures
point at the broken stage. Includes gutter run buttons, single-test re-runs,
flakiness pass rates, and a full trace webview (tool calls + judge reasoning).

Requires the `agent-harness` Python package (`pip install -e .` from the
repo) and an `OPENAI_API_KEY` in the environment VS Code was launched from.

Settings: `agentHarness.command`, `agentHarness.extraEnv`.