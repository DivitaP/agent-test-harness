import { expect, it } from "vitest";
import { TestResult } from "../src/report";
import { renderHtml } from "../src/traceHtml";

it("escapes html in tool output (webview injection protection)", () => {
  const t: TestResult = {
    name: "x", passed: false, pass_rate: 0, min_pass_rate: 1,
    scorer_pass_rates: { output: 0 },
    runs: [{
      run_index: 0, passed: false,
      scores: [{ scorer: "output", passed: false, score: 0, reason: "bad" }],
      trace: {
        input: "q",
        tool_calls: [{
          name: "t", input: "<b>q</b>",
          output: "<script>alert(1)</script>", error: null, duration_ms: 5,
        }],
        final_answer: "a", error: null, duration_ms: 9,
      },
    }],
  };
  const html = renderHtml(t, "s.yaml");
  expect(html).toContain("&lt;script&gt;");
  expect(html).not.toContain("<script>alert");
});