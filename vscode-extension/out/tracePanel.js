"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.showTracePanel = showTracePanel;
// src/tracePanel.ts
const vscode = require("vscode");
const traceHtml_1 = require("./traceHtml");
function showTracePanel(test, suitePath) {
    const panel = vscode.window.createWebviewPanel("agentHarnessTrace", `Trace: ${test.name}`, vscode.ViewColumn.Beside, {});
    panel.webview.html = (0, traceHtml_1.renderHtml)(test, suitePath);
}
//# sourceMappingURL=tracePanel.js.map