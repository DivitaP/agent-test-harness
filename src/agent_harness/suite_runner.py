"""
Wire schema -> runner -> scorers
aggregate with flakiness pass-rates
"""

import time
from pathlib import Path
from typing import Any

from agent_harness.results import RunResult, SuiteResult, TestResult
from agent_harness.runner import load_target, run_single
from agent_harness.schema import AgentTest, load_suite
from agent_harness.scorers import (
    EmbedFn,
    score_evidence,
    score_output,
    score_process,
)

def run_test(
    app: Any,
    test: AgentTest,
    judge_client: Any = None,
    embed_fn: EmbedFn | None = None,
    judge_model: str = "gpt-5.6",
) -> TestResult:
    runs: list[RunResult] = []

    for i in range(test.runs):
        trace = run_single(app, test.input)

        scores = []
        if test.process is not None:
            scores.append(score_process(test.process, trace))

        if test.evidence is not None:
            scores.append(score_evidence(test.evidence, trace, embed_fn=embed_fn))

        scores.append(
            score_output(test.output, trace, client=judge_client, model=judge_model)
        )

        runs.append(
            RunResult(
                run_index=i,
                passed=all(s.passed for s in scores),
                scores=scores,
                trace=trace,
            )
        )

    pass_rate = sum(r.passed for r in runs) / len(runs)

    scorer_pass_rates: dict[str, float] = {}
    for name in ("process", "evidence", "output"):
        relevant = [s for r in runs for s in r.scores if s.scorer == name]
        if relevant:
            scorer_pass_rates[name] = sum(s.passed for s in relevant) / len(relevant)

    return TestResult(
        name=test.name,
        passed=pass_rate >= test.min_pass_rate,
        pass_rate=pass_rate,
        min_pass_rate=test.min_pass_rate,
        scorer_pass_rates=scorer_pass_rates,
        runs=runs,
    )
    
def run_suite(
    path: str | Path,
    judge_client: Any = None,
    embed_fn: EmbedFn | None = None,
    judge_model: str = "gpt-5.6",
) -> SuiteResult:
    suite = load_suite(path)
    app = load_target(suite.target)
    start = time.monotonic()
    tests = [
        run_test(app, t, judge_client=judge_client, embed_fn=embed_fn, judge_model=judge_model)
        for t in suite.tests
    ]
    return SuiteResult(
        suite_path=str(path),
        target=suite.target,
        duration_ms=(time.monotonic() - start) * 1000,
        tests=tests,
    )
