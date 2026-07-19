// src/tracePanel.ts
import * as vscode from "vscode";
import { TestResult } from "./report";
import { renderHtml } from "./traceHtml";

export function showTracePanel(test: TestResult, suitePath: string): void {
  const panel = vscode.window.createWebviewPanel(
    "agentHarnessTrace",
    `Trace: ${test.name}`,
    vscode.ViewColumn.Beside,
    {}
  );
  panel.webview.html = renderHtml(test, suitePath);
}