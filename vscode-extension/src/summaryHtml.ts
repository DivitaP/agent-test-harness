import { Report, SuiteResult, TestResult } from "./report";

const esc = (s: unknown) =>
  String(s ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");

function scorerCards(test: TestResult): string {
  return Object.entries(test.scorer_pass_rates)
    .map(([name, rate]) => {
      const passed = rate >= test.min_pass_rate;
      return `<span class="score ${passed ? "good" : "bad"}">
        <strong>${esc(name)}</strong> ${Math.round(rate * 100)}%
      </span>`;
    })
    .join("");
}

function failureExplanation(test: TestResult): string {
  const firstFailure = test.runs
    .flatMap((run) => run.scores)
    .find((score) => !score.passed);
  if (!firstFailure) return "";
  return `<div class="explanation"><strong>What failed:</strong>
    ${esc(firstFailure.scorer)} — ${esc(firstFailure.reason)}
    <br><strong>Next:</strong> right-click this test in Test Explorer and choose
    <em>Agent Harness: Show Trace</em> to inspect the exact tool timeline.</div>`;
}

function testCard(test: TestResult): string {
  const passedRuns = test.runs.filter((run) => run.passed).length;
  return `<article class="card ${test.passed ? "pass" : "fail"}">
    <div class="card-title"><span class="icon">${test.passed ? "✓" : "!"}</span>
      <span>${esc(test.name)}</span></div>
    <div class="meta">${passedRuns}/${test.runs.length} runs passed · required ${Math.round(test.min_pass_rate * 100)}%</div>
    <div class="scores">${scorerCards(test)}</div>
    ${failureExplanation(test)}
  </article>`;
}

function suiteBlock(suite: SuiteResult): string {
  const passed = suite.tests.filter((test) => test.passed).length;
  return `<section><h2>${esc(suite.suite_path)}</h2>
    <div class="suite-meta">${passed}/${suite.tests.length} tests passed</div>
    ${suite.tests.map(testCard).join("")}
  </section>`;
}

export function renderSummaryHtml(report: Report, suitePath: string, passed: number): string {
  const total = report.total_tests;
  const headline = report.all_passed ? "All checks passed" : "Action needed";
  const subtitle = report.all_passed
    ? "Your agent followed the expected process and produced acceptable answers."
    : "The agent produced a result, but one or more quality checks failed.";
  return `<!DOCTYPE html><html><head><style>
    :root { color-scheme: light dark; }
    body { font-family: var(--vscode-font-family); color: var(--vscode-foreground); padding: 1.2rem 2rem; max-width: 1000px; }
    h1 { margin-bottom: .2rem; font-size: 1.8rem; }
    h2 { margin-top: 1.8rem; font-size: 1rem; opacity: .85; }
    .hero { border-radius: 10px; padding: 1.1rem 1.3rem; margin-bottom: 1.5rem; background: ${report.all_passed ? "color-mix(in srgb, var(--vscode-testing-iconPassed) 16%, transparent)" : "color-mix(in srgb, var(--vscode-testing-iconFailed) 16%, transparent)"}; border: 1px solid ${report.all_passed ? "var(--vscode-testing-iconPassed)" : "var(--vscode-testing-iconFailed)"}; }
    .hero strong { font-size: 1.25rem; }
    .hero .count { font-size: 1.8rem; font-weight: 700; margin-right: .8rem; }
    .subtitle, .meta, .suite-meta { opacity: .72; }
    .card { border-left: 4px solid; border-radius: 7px; padding: .8rem 1rem; margin: .7rem 0; background: var(--vscode-editor-inactiveSelectionBackground); }
    .card.pass { border-color: var(--vscode-testing-iconPassed); }
    .card.fail { border-color: var(--vscode-testing-iconFailed); }
    .card-title { display: flex; gap: .55rem; align-items: center; font-weight: 600; }
    .icon { display: inline-flex; width: 1.4rem; height: 1.4rem; border-radius: 50%; align-items: center; justify-content: center; color: white; background: var(--vscode-testing-iconPassed); }
    .fail .icon { background: var(--vscode-testing-iconFailed); }
    .meta { margin: .35rem 0 .55rem 2rem; font-size: .9rem; }
    .scores { display: flex; gap: .45rem; flex-wrap: wrap; margin-left: 2rem; }
    .score { border-radius: 4px; padding: .2rem .5rem; font-size: .85rem; background: var(--vscode-badge-background); }
    .score.good { border-bottom: 2px solid var(--vscode-testing-iconPassed); }
    .score.bad { border-bottom: 2px solid var(--vscode-testing-iconFailed); }
    .explanation { margin: .8rem 0 .1rem 2rem; padding: .65rem; border-radius: 4px; background: var(--vscode-textBlockQuote-background); line-height: 1.45; }
    code { font-family: var(--vscode-editor-font-family); }
  </style></head><body>
    <div class="hero"><span class="count">${passed}/${total}</span><strong>${headline}</strong>
      <div class="subtitle">${subtitle}</div>
    </div>
    <p class="subtitle">Suite: ${esc(suitePath)}</p>
    ${report.suites.map(suiteBlock).join("")}
  </body></html>`;
}
