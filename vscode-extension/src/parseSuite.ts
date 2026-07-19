import { isMap, isSeq, parseDocument } from "yaml";

export interface TestMeta {
  name: string;
  start: number;      // char offset of the test node, for gutter ranges
  end: number;
  scorers: string[];  // configured scorers; "output" always present
}
export interface SuiteMeta { target: string; tests: TestMeta[] }
export interface ParseFailure { error: string }

export function isFailure(r: SuiteMeta | ParseFailure): r is ParseFailure {
  return "error" in r;
}

export function parseSuite(text: string): SuiteMeta | ParseFailure {
  const doc = parseDocument(text);
  if (doc.errors.length) return { error: doc.errors[0].message };
  const root = doc.contents;
  if (!isMap(root)) return { error: "suite must be a YAML mapping" };

  const target = root.get("target");
  if (typeof target !== "string") return { error: "missing 'target'" };

  const seq = root.get("tests", true);
  if (!isSeq(seq)) return { error: "missing 'tests' list" };

  const tests: TestMeta[] = [];
  for (const node of seq.items) {
    if (!isMap(node) || !node.range) continue;
    const name = node.get("name");
    if (typeof name !== "string") continue;
    const scorers = ["process", "evidence"].filter((s) => node.has(s));
    scorers.push("output");
    tests.push({ name, start: node.range[0], end: node.range[1], scorers });
  }
  return { target, tests };
}