// src/traceHtml.ts
import { TestResult } from "./report";

const esc = (s: unknown) =>
  String(s ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");

export function renderHtml(test: TestResult, suitePath: string): string {
  const runs = test.runs
    .map(
      (r) => `
  <section class="${r.passed ? "pass" : "fail"}">
    <h2>Run ${r.run_index + 1}: ${r.passed ? "PASS" : "FAIL"}
      <small>${Math.round(r.trace.duration_ms ?? 0)} ms</small></h2>
    <h3>Scores</h3>
    <table>
      <tr><th>Scorer</th><th>Score</th><th>Verdict</th><th>Reason</th></tr>
      ${r.scores
        .map(
          (s) => `<tr class="${s.passed ? "pass" : "fail"}">
        <td>${esc(s.scorer)}</td><td>${s.score.toFixed(2)}</td>
        <td>${s.passed ? "pass" : "fail"}</td><td>${esc(s.reason)}</td></tr>`
        )
        .join("")}
    </table>
    <h3>Tool calls</h3>
    ${
      r.trace.tool_calls.length
        ? `<table>
      <tr><th>#</th><th>Tool</th><th>Input</th><th>Output / Error</th><th>ms</th></tr>
      ${r.trace.tool_calls
        .map(
          (c, i) => `<tr>
        <td>${i + 1}</td><td>${esc(c.name)}</td>
        <td><pre>${esc(c.input)}</pre></td>
        <td><pre class="${c.error ? "fail" : ""}">${esc(c.error ?? c.output)}</pre></td>
        <td>${c.duration_ms == null ? "" : Math.round(c.duration_ms)}</td></tr>`
        )
        .join("")}
    </table>`
        : `<p class="fail">No tool calls recorded.</p>`
    }
    <h3>Final answer</h3>
    <pre>${esc(r.trace.final_answer || r.trace.error)}</pre>
  </section>`
    )
    .join("");

  return `<!DOCTYPE html><html><head><style>
    body { font-family: var(--vscode-font-family); color: var(--vscode-foreground); padding: 0 1rem; }
    table { border-collapse: collapse; width: 100%; margin: .3rem 0 .8rem; }
    th, td { border: 1px solid var(--vscode-widget-border, #444); padding: 4px 8px; text-align: left; vertical-align: top; }
    pre { white-space: pre-wrap; margin: 0; max-height: 12em; overflow: auto; }
    section { border-left: 3px solid; padding-left: .8rem; margin: 1rem 0; }
    section.pass { border-color: var(--vscode-testing-iconPassed, #3c3); }
    section.fail { border-color: var(--vscode-testing-iconFailed, #c33); }
    tr.fail td, pre.fail, p.fail { color: var(--vscode-testing-iconFailed, #c33); }
    small { opacity: .6; font-weight: normal; }
  </style></head><body>
    <h1>${esc(test.name)}</h1>
    <p><small>${esc(suitePath)}, pass rate ${test.pass_rate.toFixed(2)}
      (required ${test.min_pass_rate.toFixed(2)})</small></p>
    ${runs}
  </body></html>`;
}