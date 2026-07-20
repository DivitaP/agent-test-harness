"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.activate = activate;
exports.deactivate = deactivate;
const vscode = require("vscode");
const parseSuite_1 = require("./parseSuite");
const report_1 = require("./report");
const runner_1 = require("./runner");
const summaryPanel_1 = require("./summaryPanel");
const tracePanel_1 = require("./tracePanel");
const lastResults = new Map(); // test item id -> latest result
const lastReports = new Map(); // suite item id -> latest report
function activate(context) {
    const controller = vscode.tests.createTestController("agentHarness", "Agent Harness");
    context.subscriptions.push(controller);
    const suiteExcludeGlob = () => {
        const excluded = vscode.workspace
            .getConfiguration("agentHarness")
            .get("exclude", ["**/node_modules/**"]);
        return excluded.length ? `{${excluded.join(",")}}` : undefined;
    };
    // --- discovery: suite file -> tests -> scorer children -------------
    const discover = async (uri) => {
        const doc = await vscode.workspace.openTextDocument(uri);
        const parsed = (0, parseSuite_1.parseSuite)(doc.getText());
        const suiteItem = controller.createTestItem(uri.toString(), vscode.workspace.asRelativePath(uri), uri);
        if ((0, parseSuite_1.isFailure)(parsed)) {
            suiteItem.error = parsed.error; // surfaces schema mistakes in the UI
            controller.items.add(suiteItem);
            return;
        }
        suiteItem.children.replace(parsed.tests.map((t) => {
            const id = `${uri}#${t.name}`;
            const item = controller.createTestItem(id, t.name, uri);
            item.range = new vscode.Range(doc.positionAt(t.start), doc.positionAt(t.end));
            item.children.replace(t.scorers.map((s) => controller.createTestItem(`${id}#${s}`, s, uri)));
            return item;
        }));
        controller.items.add(suiteItem);
    };
    vscode.workspace
        .findFiles("**/*.agent-test.yaml", suiteExcludeGlob())
        .then((uris) => uris.forEach(discover));
    const watcher = vscode.workspace.createFileSystemWatcher("**/*.agent-test.yaml");
    watcher.onDidCreate(discover);
    watcher.onDidChange(discover);
    watcher.onDidDelete((uri) => controller.items.delete(uri.toString()));
    context.subscriptions.push(watcher);
    // --- helpers --------------------------------------------------------
    const suiteOf = (item) => {
        let cur = item;
        while (cur.parent)
            cur = cur.parent;
        return cur;
    };
    // suite -> itself; test -> itself; scorer child -> its parent test
    const testItemOf = (item) => !item.parent ? item : item.parent.parent ? item.parent : item;
    const markStarted = (run, suite, names) => {
        suite.children.forEach((t) => {
            if (!names || names.has(t.label)) {
                run.started(t);
                t.children.forEach((s) => run.started(s));
            }
        });
    };
    const applyReport = (run, suite, report) => {
        const byName = new Map();
        for (const s of report.suites)
            for (const t of s.tests)
                byName.set(t.name, t);
        suite.children.forEach((testItem) => {
            const result = byName.get(testItem.label);
            if (!result)
                return; // filtered out of this run
            lastResults.set(testItem.id, result);
            const outcome = (0, report_1.summarizeTest)(result);
            testItem.description = `${result.pass_rate.toFixed(2)} pass rate · ${outcome.passed ? "all checks passed" : "action needed"}`;
            testItem.children.forEach((scorerItem) => {
                const s = outcome.scorers[scorerItem.label];
                if (!s)
                    return run.skipped(scorerItem);
                scorerItem.description = `${(result.scorer_pass_rates[scorerItem.label] * 100).toFixed(0)}%`;
                s.passed
                    ? run.passed(scorerItem)
                    : run.failed(scorerItem, new vscode.TestMessage(s.message ?? "failed"));
            });
            outcome.passed
                ? run.passed(testItem, outcome.durationMs)
                : run.failed(testItem, new vscode.TestMessage(outcome.message ?? "failed"), outcome.durationMs);
        });
    };
    // --- run profile -----------------------------------------------------
    controller.createRunProfile("Run", vscode.TestRunProfileKind.Run, async (request, token) => {
        const run = controller.createTestRun(request);
        const abort = new AbortController();
        token.onCancellationRequested(() => abort.abort());
        const roots = [];
        if (request.include)
            roots.push(...request.include);
        else
            controller.items.forEach((i) => roots.push(i));
        // group requested items by suite file; undefined names = whole file
        const bySuite = new Map();
        for (const item of roots) {
            const suite = suiteOf(item);
            const entry = bySuite.get(suite.id) ?? { suite, names: new Set() };
            if (item === suite)
                entry.names = undefined;
            else
                entry.names?.add(testItemOf(item).label);
            bySuite.set(suite.id, entry);
        }
        const config = vscode.workspace.getConfiguration("agentHarness");
        const command = config.get("command", "agent-harness");
        const extraEnv = config.get("extraEnv", {});
        for (const { suite, names } of bySuite.values()) {
            const uri = suite.uri;
            const cwd = vscode.workspace.getWorkspaceFolder(uri)?.uri.fsPath ?? "";
            markStarted(run, suite, names);
            const outcome = await (0, runner_1.runCli)({
                command,
                suitePath: uri.fsPath,
                cwd,
                env: { ...process.env, ...extraEnv },
                testNames: names && [...names],
                signal: abort.signal,
            });
            if (outcome.kind === "error") {
                run.errored(suite, new vscode.TestMessage(outcome.message));
                continue;
            }
            lastReports.set(suite.id, outcome.report);
            applyReport(run, suite, outcome.report);
            // Put the explanation in front of the developer immediately; the
            // Test Explorer remains available for reruns and individual traces.
            (0, summaryPanel_1.showSummaryPanel)(outcome.report, uri.fsPath);
        }
        run.end();
    }, true);
    // --- trace command -----------------------------------------------------
    context.subscriptions.push(vscode.commands.registerCommand("agentHarness.showTrace", (item) => {
        if (!item) {
            vscode.window.showInformationMessage("Right-click a test in the Test Explorer.");
            return;
        }
        const test = testItemOf(item);
        const result = lastResults.get(test.id);
        if (!result) {
            vscode.window.showInformationMessage("Run this test first.");
            return;
        }
        (0, tracePanel_1.showTracePanel)(result, vscode.workspace.asRelativePath(test.uri));
    }));
    context.subscriptions.push(vscode.commands.registerCommand("agentHarness.showSummary", (item) => {
        const suite = item ? suiteOf(item) : undefined;
        const report = suite ? lastReports.get(suite.id) : [...lastReports.values()].at(-1);
        if (!report) {
            vscode.window.showInformationMessage("Run Agent Harness tests first to see a results summary.");
            return;
        }
        (0, summaryPanel_1.showSummaryPanel)(report, suite?.uri ? vscode.workspace.asRelativePath(suite.uri) : "latest run");
    }));
}
function deactivate() { }
//# sourceMappingURL=extension.js.map