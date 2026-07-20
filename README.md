# Agent Test Harness for LangGraph

Semantic testing for agentic pipelines: a Python CLI plus a VS Code extension.
Write tests against what your agent should *do*, not the exact string it
returns. Every run is scored on three independent stages, so a failed test
tells you *which stage broke*:

- **process**: did the agent take the right steps (expected tool trajectory,
  order-aware, partial credit via longest common subsequence)
- **evidence**: did it gather grounding before answering (presence check plus
  optional embedding-relevance threshold)
- **output**: does the final answer satisfy a natural-language rubric
  (GPT-5.6 as judge, temperature 0, structured verdict)

The one-line pitch: an agent that answers "36" without ever calling the
calculator passes every string-match framework. This harness fails it, with
`process 0.00 | output 1.00`, and shows you the empty tool-call trace.

## Why three scorers

The design applies the reflection-loop pattern from the Bayer/Thoughtworks
production case study ("Building Reliable Agentic AI Systems",
martinfowler.com): check process quality, evidence sufficiency, and final
answer quality *separately*, because they fail independently and mean
different bugs. Here that pattern is a testing primitive instead of a
runtime safeguard.

## Architecture

    .agent-test.yaml ──> suite runner ──> traced run (LangGraph callbacks)
                              │                      │
                              │          Trace: tool calls, evidence, answer
                              ▼                      ▼
                  process scorer    evidence scorer    output scorer (GPT-5.6)
                              └───────────┬──────────┘
                        JSON report (per-scorer pass rates over N runs)
                              ┌───────────┴──────────┐
                        CLI console          VS Code Test Explorer + trace webview

Tracing needs zero agent instrumentation: LangGraph propagates config to
every node, so a callback handler attached at `invoke()` sees each tool
call's name, input, output, error, and timing.

## Quick start

    python -m venv .venv && source .venv/bin/activate
    pip install -e ".[dev,demo]"
    pytest                       # offline tests, no API key needed

    export OPENAI_API_KEY=sk-...
    agent-harness run demo_tests/

## Support Desk example

The repository includes a complete fictional refund agent in
[`examples/support_desk`](examples/support_desk/). It demonstrates why agent
tests need more than an answer check: in `skip_policy` mode the agent gives a
confident, correct-looking refund answer while skipping a required policy
lookup.

    agent-harness run examples/support_desk/support_tests/
    DEMO_FAILURE_MODE=skip_policy agent-harness run examples/support_desk/support_tests/

The example works offline for repeatable tests. To use the live Streamlit demo,
install the `demo` extras and set `GROQ_API_KEY`, then run:

    streamlit run examples/support_desk/scripts/support_ui.py

## Test file reference

    target: "demo_agent.graph:app"     # import path to a compiled LangGraph
    tests:
      - name: "topic search then detail fetch"
        input: "Find the study about sleep quality and summarize it."
        process:                        # optional
          expected_tools: ["search_studies", "get_study_details"]
          strict_order: true            # ordered subsequence; false = multiset
          forbidden_tools: ["delete_study"]  # optional safety guard
        evidence:                       # optional
          required: true
          required_tools: ["get_study_details"]  # optional required source
          min_relevance: 0.3            # optional cosine threshold vs task
        output:                         # required
          rubric: "Must cite SL-88 and the 22 percent latency improvement."
          threshold: 0.7
        runs: 5                         # flakiness: repeat N times
        min_pass_rate: 0.9              # fraction of runs that must pass

## Live failure demo

The demo agent has injectable failure modes (env var, agent code unchanged):

    agent-harness run demo_tests/                                  # baseline
    DEMO_FAILURE_MODE=vague_answers   agent-harness run demo_tests/  # output-only failures
    DEMO_FAILURE_MODE=answer_directly agent-harness run demo_tests/  # process+evidence failures
    DEMO_FAILURE_MODE=flaky_search    agent-harness run demo_tests/  # pass rates < 1.0

## VS Code extension

Each test appears in the native Test Explorer with three scorer children,
run buttons in the YAML gutter, single-test re-runs, and a trace webview
(right-click > Agent Harness: Show Trace) showing per-run scores, the
tool-call table, and the judge's reasoning. Settings: `agentHarness.command`
(CLI invocation) and `agentHarness.extraEnv` (e.g. DEMO_FAILURE_MODE).

## Evaluation

`python eval/run_eval.py` injects each failure mode and verifies the harness
flags the broken stage while healthy stages stay green. Results:
[eval/results.md](eval/results.md).

## Built with

Built new for the OpenAI hackathon (Developer Tools). Developed with Codex.
GPT-5.6 is structural: it drives the demo agent's tool choice and serves as
the output judge.

## Limitations

- LangGraph only (callback-based tracing generalizes; other frameworks are roadmap)
- Judge scores are LLM judgments: threshold + temperature 0 + auto-fail
  short-circuits reduce variance but do not eliminate it
- `agentHarness.command` splits on whitespace, so interpreter paths with
  spaces need a shim script
- Evidence relevance uses embedding similarity, a proxy for actual grounding

MIT licensed.
