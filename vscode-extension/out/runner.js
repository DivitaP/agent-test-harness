"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.runCli = runCli;
const node_child_process_1 = require("node:child_process");
const report_1 = require("./report");
function runCli(opts) {
    const { cmd, args } = (0, report_1.buildCommand)(opts.command, opts.suitePath, opts.testNames);
    return new Promise((resolve) => {
        const child = (0, node_child_process_1.spawn)(cmd, args, { cwd: opts.cwd, env: opts.env, signal: opts.signal });
        let out = "";
        let err = "";
        child.stdout.on("data", (d) => (out += d));
        child.stderr.on("data", (d) => (err += d));
        child.on("error", (e) => resolve({ kind: "error", message: String(e) }));
        child.on("close", (code) => {
            if (code === 0 || code === 1) {
                // both carry a valid JSON report; 1 just means some tests failed
                try {
                    resolve({ kind: "report", report: (0, report_1.parseReport)(out) });
                }
                catch {
                    resolve({ kind: "error", message: `unparseable report:\n${out.slice(0, 400)}` });
                }
            }
            else {
                resolve({ kind: "error", message: err || `exit code ${code}` });
            }
        });
    });
}
//# sourceMappingURL=runner.js.map