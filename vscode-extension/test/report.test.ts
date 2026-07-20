import { expect, it } from "vitest";
import { buildCommand, summarizeTest, TestResult } from "../src/report";

const base = (over: Partial<TestResult>): TestResult => ({
  name: "t",
  passed: true,
  pass_rate: 1,
  min_pass_rate: 1,
  scorer_pass_rates: { output: 1 },
  runs: [
    {
      run_index: 0,
      passed: true,
      scores: [{ scorer: "output", passed: true, score: 1, reason: "ok" }],
      trace: { input: "q", tool_calls: [], final_answer: "a", error: null, duration_ms: 120 },
    },
  ],
  ...over,
});

it("passing test: scorers pass, duration summed", () => {
  const o = summarizeTest(base({}));
  expect(o.passed).toBe(true);
  expect(o.scorers.output.passed).toBe(true);
  expect(o.durationMs).toBe(120);
});

it("failing scorer carries rate and first failure reason", () => {
  const o = summarizeTest(
    base({
      passed: false,
      pass_rate: 0,
      scorer_pass_rates: { evidence: 0, output: 1 },
      runs: [
        {
          run_index: 0,
          passed: false,
          scores: [
            { scorer: "evidence", passed: false, score: 0, reason: "answered without evidence" },
            { scorer: "output", passed: true, score: 0.9, reason: "fine" },
          ],
          trace: { input: "q", tool_calls: [], final_answer: "a", error: null, duration_ms: 80 },
        },
      ],
    })
  );
  expect(o.scorers.evidence.passed).toBe(false);
  expect(o.scorers.evidence.message).toContain("answered without evidence");
  expect(o.scorers.output.passed).toBe(true);
  expect(o.message).toContain("evidence 0.00");
});

it("flaky: scorer passes when rate meets min_pass_rate", () => {
  const o = summarizeTest(
    base({ min_pass_rate: 0.5, pass_rate: 0.5, scorer_pass_rates: { output: 0.5 } })
  );
  expect(o.scorers.output.passed).toBe(true);
});

it("buildCommand splits multi-word command and appends filters", () => {
  const { cmd, args } = buildCommand("python -m agent_harness.cli", "/x/s.agent-test.yaml", ["a b"]);
  expect(cmd).toBe("python");
  expect(args).toEqual([
    "-m", "agent_harness.cli", "run", "/x/s.agent-test.yaml", "--json", "--test", "a b",
  ]);
});