import { expect, it } from "vitest";
import { isFailure, parseSuite } from "../src/parseSuite";

const SUITE = `
target: "demo_agent.graph:app"
tests:
  - name: "lookup"
    input: "q"
    process:
      expected_tools: ["get_study_details"]
    evidence:
      required: true
    output:
      rubric: "r"
  - name: "math"
    input: "q2"
    output:
      rubric: "r2"
`;

it("extracts target, names, offsets, scorers", () => {
  const r = parseSuite(SUITE);
  if (isFailure(r)) throw new Error(r.error);
  expect(r.target).toBe("demo_agent.graph:app");
  expect(r.tests.map((t) => t.name)).toEqual(["lookup", "math"]);
  expect(r.tests[0].scorers).toEqual(["process", "evidence", "output"]);
  expect(r.tests[1].scorers).toEqual(["output"]);
  expect(SUITE.slice(r.tests[0].start, r.tests[0].end)).toContain('name: "lookup"');
});

it("reports invalid yaml", () => {
  expect(isFailure(parseSuite("tests: [::"))).toBe(true);
});

it("reports missing target", () => {
  const r = parseSuite("tests:\n  - name: x\n    input: q\n    output: {rubric: r}");
  expect(isFailure(r) && r.error).toMatch(/target/);
});