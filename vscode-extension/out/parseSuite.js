"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.isFailure = isFailure;
exports.parseSuite = parseSuite;
const yaml_1 = require("yaml");
function isFailure(r) {
    return "error" in r;
}
function parseSuite(text) {
    const doc = (0, yaml_1.parseDocument)(text);
    if (doc.errors.length)
        return { error: doc.errors[0].message };
    const root = doc.contents;
    if (!(0, yaml_1.isMap)(root))
        return { error: "suite must be a YAML mapping" };
    const target = root.get("target");
    if (typeof target !== "string")
        return { error: "missing 'target'" };
    const seq = root.get("tests", true);
    if (!(0, yaml_1.isSeq)(seq))
        return { error: "missing 'tests' list" };
    const tests = [];
    for (const node of seq.items) {
        if (!(0, yaml_1.isMap)(node) || !node.range)
            continue;
        const name = node.get("name");
        if (typeof name !== "string")
            continue;
        const scorers = ["process", "evidence"].filter((s) => node.has(s));
        scorers.push("output");
        tests.push({ name, start: node.range[0], end: node.range[1], scorers });
    }
    return { target, tests };
}
//# sourceMappingURL=parseSuite.js.map