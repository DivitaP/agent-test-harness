"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.parseReport = parseReport;
exports.summarizeTest = summarizeTest;
exports.buildCommand = buildCommand;
function parseReport(json) {
    return JSON.parse(json);
}
/** A scorer passes iff its cross-run pass rate meets the test's min_pass_rate.
 *  For runs=1 / min_pass_rate=1.0 this reduces to exact per-scorer pass/fail. */
function summarizeTest(t) {
    const durationMs = t.runs.reduce((ms, r) => ms + (r.trace.duration_ms ?? 0), 0);
    const scorers = {};
    for (const [name, rate] of Object.entries(t.scorer_pass_rates)) {
        const passed = rate >= t.min_pass_rate;
        scorers[name] = { passed, message: passed ? undefined : failReason(t, name, rate) };
    }
    return {
        passed: t.passed,
        durationMs,
        message: t.passed ? undefined : testMessage(t),
        scorers,
    };
}
function failReason(t, scorer, rate) {
    const firstFail = t.runs
        .flatMap((r) => r.scores)
        .find((s) => s.scorer === scorer && !s.passed);
    const rateTxt = `pass rate ${rate.toFixed(2)} < required ${t.min_pass_rate.toFixed(2)}`;
    return firstFail ? `${rateTxt}\n${firstFail.reason}` : rateTxt;
}
function testMessage(t) {
    const passes = t.runs.filter((r) => r.passed).length;
    const breakdown = Object.entries(t.scorer_pass_rates)
        .map(([k, v]) => `${k} ${v.toFixed(2)}`)
        .join(" | ");
    return `runs ${passes}/${t.runs.length} passed (need ${t.min_pass_rate.toFixed(2)})  [${breakdown}]`;
}
function buildCommand(setting, suitePath, testNames) {
    const parts = setting.trim().split(/\s+/);
    const args = [...parts.slice(1), "run", suitePath, "--json"];
    for (const n of testNames ?? [])
        args.push("--test", n);
    return { cmd: parts[0], args };
}
//# sourceMappingURL=report.js.map