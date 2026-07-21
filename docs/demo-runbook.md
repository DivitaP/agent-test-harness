# Support Desk demo runbook

This is a four-minute VS Code demo. Keep the story focused on one point: a
plausible answer is not proof that an agent behaved safely.

## Before presenting

From the repository root, run `bash scripts/bootstrap_demo.sh`. Open
`vscode-extension/` in VS Code and press `F5`. In the Extension Development
Host window, open the repository root and then open the Testing panel. The
workspace configuration shows only the Support Desk suite.

## 1. Explain the product (20 seconds)

Show the architecture image.

![Agent Harness architecture](images/agent_harness_architecture.png)

Say: “Agent Harness turns agent behavior into a testable contract. A test
specifies a task, expected tool behavior, evidence requirements, and an output
rubric. The agent runs repeatedly, and the harness scores process, evidence,
and output independently.”

## 2. Establish a healthy baseline (40 seconds)

Open `examples/support_desk/support_tests/refunds.agent-test.yaml`. Point to
the damaged-refund test and its required sequence:

```yaml
expected_tools: [lookup_order, check_refund_policy, issue_refund]
required_tools: [lookup_order, check_refund_policy]
```

Run the Support Desk suite in Test Explorer. The automatic results panel shows
all four tests passing. Say: “The agent looked up the order, grounded its
eligibility decision in policy, and issued the refund. The in-transit test also
proves it does not issue a prohibited refund.”

## 3. Explain the silent regression (25 seconds)

Show this image before changing any setting.

![Healthy behavior compared with the skip-policy regression](images/skip_policy_regression_story.png)

Say: “This is the failure that answer-only testing misses. The final answer can
still look correct, even when the required policy lookup disappeared.”

## 4. Reproduce it in VS Code (50 seconds)

In `.vscode/settings.json`, set:

```json
"agentHarness.extraEnv": {
  "DEMO_FAILURE_MODE": "skip_policy"
}
```

Rerun the suite. The damaged-refund test fails while the other tests remain
green. The results panel should read:

```text
Process   FAIL
Evidence  FAIL
Output    PASS
```

Say: “The answer passes, but the agent failed the process and evidence checks.
That is exactly the distinction developers need when testing agents.”

## 5. Diagnose in one click (35 seconds)

Click **View trace** on the failed result card. Point to the observed calls:

```text
lookup_order
issue_refund
```

Say: “The trace is the handoff from a failed evaluation to a concrete fix:
`check_refund_policy` is missing. The developer does not have to replay the
conversation or search through logs.”

## Closing line (15 seconds)

Say: “Agent Harness verifies what an agent did, what it grounded on, and what
it said—inside the developer workflow where failures are fixed.”

Restore `.vscode/settings.json` to `"agentHarness.extraEnv": {}` after the
demo.
