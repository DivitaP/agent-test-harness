import { spawn } from "node:child_process";
import { buildCommand, parseReport, Report } from "./report";

export type CliOutcome =
  | { kind: "report"; report: Report }
  | { kind: "error"; message: string };

export function runCli(opts: {
  command: string;
  suitePath: string;
  cwd: string;
  env: NodeJS.ProcessEnv;
  testNames?: string[];
  signal?: AbortSignal;
}): Promise<CliOutcome> {
  const { cmd, args } = buildCommand(opts.command, opts.suitePath, opts.testNames);
  return new Promise((resolve) => {
    const child = spawn(cmd, args, { cwd: opts.cwd, env: opts.env, signal: opts.signal });
    let out = "";
    let err = "";
    child.stdout.on("data", (d) => (out += d));
    child.stderr.on("data", (d) => (err += d));
    child.on("error", (e) => resolve({ kind: "error", message: String(e) }));
    child.on("close", (code) => {
      if (code === 0 || code === 1) {
        // both carry a valid JSON report; 1 just means some tests failed
        try {
          resolve({ kind: "report", report: parseReport(out) });
        } catch {
          resolve({ kind: "error", message: `unparseable report:\n${out.slice(0, 400)}` });
        }
      } else {
        resolve({ kind: "error", message: err || `exit code ${code}` });
      }
    });
  });
}