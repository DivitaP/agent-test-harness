import * as vscode from "vscode";
import { Report } from "./report";
import { renderSummaryHtml } from "./summaryHtml";
import { showTracePanel } from "./tracePanel";

export function showSummaryPanel(report: Report, suitePath: string): void {
  const passed = report.suites.reduce(
    (count, suite) => count + suite.tests.filter((test) => test.passed).length,
    0
  );
  const panel = vscode.window.createWebviewPanel(
    "agentHarnessSummary",
    `${report.all_passed ? "✓" : "!"} Agent Harness Results`,
    vscode.ViewColumn.One,
    { enableFindWidget: true }
  );
  panel.webview.html = renderSummaryHtml(report, suitePath, passed);
  panel.webview.onDidReceiveMessage((message: { command?: string; testName?: string }) => {
    if (message.command !== "openTrace" || !message.testName) return;
    const test = report.suites
      .flatMap((suite) => suite.tests)
      .find((candidate) => candidate.name === message.testName);
    if (test) showTracePanel(test, suitePath);
  });
}
