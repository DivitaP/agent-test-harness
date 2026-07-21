# Agent Harness for VS Code

Semantic testing for LangGraph agents in the native Test Explorer. Each test
expands into three scorer results (process, evidence, output), so failures
point at the broken stage. Includes gutter run buttons, single-test re-runs,
flakiness pass rates, and a full trace webview (tool calls + judge reasoning).

Requires the `agent-harness` Python package (`pip install -e .` from the
repo). The extension itself works offline. A live model key depends on the
target agent: the included Support Desk agent uses `GROQ_API_KEY`; the separate
research example uses `OPENAI_API_KEY` by default.

Settings: `agentHarness.command`, `agentHarness.extraEnv`.
