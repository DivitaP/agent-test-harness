"""
agent harness CLI
run suites, emit console or JSON reports

Exit codes: 0 all tests passed, 1 at least one test failed,
2 usage/config error (bad path, invalid YAML, unimportable target).
"""

import argparse
import os
import sys
from pathlib import Path
from typing import Any

from agent_harness.results import Report
from agent_harness.schema import discover_suites
from agent_harness.scorers import DEFAULT_JUDGE_MODEL
from agent_harness.suite_runner import run_suite

def _render_console(report: Report) -> None:
    for suite in report.suites:
        print(f"\nsuite {suite.suite_path} (target {suite.target})")
        for t in suite.tests:
            mark = "PASS" if t.passed else "FAIL"
            n_passed = sum(r.passed for r in t.runs)
            breakdown = " | ".join(
                f"{k} {v:.2f}" for k,v in t.scorer_pass_rates.items()
            )
            print(f" [{mark}] {t.name} runs {n_passed}/{len(t.runs)} [{breakdown}]")
            if not t.passed:
                first_fail = next(r for r in t.runs if not r.passed)
                for s in first_fail.scores:
                    if not s.passed:
                        print(f"    {s.scorer}: {s.reason}")
    print(f"\n{report.passed_tests}/{report.total_tests} tests passed")

def main(
    argv: list[str] | None=None,
    judge_client: Any=None,
    embed_fn: Any = None,
) -> int:
    parser = argparse.ArgumentParser(
        prog="agent-harness", description="Semantic testing for LangGraph agents"
    )
    sub = parser.add_subparsers(dest="command", required=True)
    run_p = sub.add_parser("run", help="run .agent-test.yaml suites")
    run_p.add_argument("path", help="a .agent-test.yaml file or a directory to search")
    run_p.add_argument("--json", action="store_true", help="print JSON report to stdout")
    run_p.add_argument("--output", help="also write the JSON report to this file")
    run_p.add_argument("--judge-model", default=DEFAULT_JUDGE_MODEL)

    args = parser.parse_args(argv)

    path = Path(args.path)

    if path.is_file():
        suite_paths = [path]
    elif path.is_dir():
        suite_paths = discover_suites(path)
        if not suite_paths:
            print(f"no .agent-test.yaml files found under {path}", file=sys.stderr)
            return 2
        
    else:
        print(f"path not found: {path}", file=sys.stderr)
        return 2
    
    sys.path.insert(0, os.getcwd()) # makes the users project importable as target

    suites = []
    for sp in suite_paths:
        try:
            suites.append(
                run_suite(
                    sp,
                    judge_client=judge_client,
                    embed_fn=embed_fn,
                    judge_model=args.judge_model,
                )
            )
        except Exception as e: # config errors, not test failures
            print(f"error in {sp}: {type(e).__name__}: {e}", file=sys.stderr)
            return 2
        
    report = Report(suites=suites)
    payload = report.model_dump_json(indent=2)
    if args.output:
        Path(args.output).write_text(payload)
    if args.json:
        print(payload)
    else:
        _render_console(report)
    
    return 0 if report.all_passed else 1
