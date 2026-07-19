export interface ScoreResult { scorer: string; passed: boolean; score: number; reason: string }
export interface ToolCall {
  name: string; input: string; output: string | null;
  error: string | null; duration_ms: number | null;
}
export interface Trace {
  input: string; tool_calls: ToolCall[]; final_answer: string;
  error: string | null; duration_ms: number | null;
}
export interface RunResult { run_index: number; passed: boolean; scores: ScoreResult[]; trace: Trace }
export interface TestResult {
  name: string; passed: boolean; pass_rate: number; min_pass_rate: number;
  scorer_pass_rates: Record<string, number>; runs: RunResult[];
}
export interface SuiteResult { suite_path: string; target: string; tests: TestResult[] }
export interface Report { suites: SuiteResult[]; all_passed: boolean; total_tests: number }

export function parseReport(json: string): Report {
  return JSON.parse(json) as Report;
}

export interface ScorerOutcome { passed: boolean; message?: string }
export interface TestOutcome {
  passed: boolean;
  durationMs: number;
  message?: string;
  scorers: Record<string, ScorerOutcome>;
}

/** A scorer passes iff its cross-run pass rate meets the test's min_pass_rate.
 *  For runs=1 / min_pass_rate=1.0 this reduces to exact per-scorer pass/fail. */
export function summarizeTest(t: TestResult): TestOutcome {
  const durationMs = t.runs.reduce((ms, r) => ms + (r.trace.duration_ms ?? 0), 0);
  const scorers: Record<string, ScorerOutcome> = {};
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

function failReason(t: TestResult, scorer: string, rate: number): string {
  const firstFail = t.runs
    .flatMap((r) => r.scores)
    .find((s) => s.scorer === scorer && !s.passed);
  const rateTxt = `pass rate ${rate.toFixed(2)} < required ${t.min_pass_rate.toFixed(2)}`;
  return firstFail ? `${rateTxt}\n${firstFail.reason}` : rateTxt;
}

function testMessage(t: TestResult): string {
  const passes = t.runs.filter((r) => r.passed).length;
  const breakdown = Object.entries(t.scorer_pass_rates)
    .map(([k, v]) => `${k} ${v.toFixed(2)}`)
    .join(" | ");
  return `runs ${passes}/${t.runs.length} passed (need ${t.min_pass_rate.toFixed(2)})  [${breakdown}]`;
}

export function buildCommand(setting: string, suitePath: string, testNames?: string[]) {
  const parts = setting.trim().split(/\s+/);
  const args = [...parts.slice(1), "run", suitePath, "--json"];
  for (const n of testNames ?? []) args.push("--test", n);
  return { cmd: parts[0], args };
}