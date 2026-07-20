"""Meta-evaluation: does the harness flag injected failures at the right stage?

Runs the demo suite once per failure mode and reports per-scorer pass rates,
plus detection/isolation counts. Live script: requires OPENAI_API_KEY.
Cost: ~40-60 LLM calls (about a dollar). Usage: python eval/run_eval.py
"""
import argparse
import os
import sys
from pathlib import Path

# Run against this checkout rather than whichever agent_harness package happens
# to be installed in the active Python environment.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))
sys.path.insert(0, str(PROJECT_ROOT))

from agent_harness.suite_runner import run_suite  # noqa: E402

SUITE = PROJECT_ROOT / "demo_tests/research.agent-test.yaml"
MODES = ["none", "vague_answers", "answer_directly", "flaky_search"]

# Which scorers each mode should break. Notes:
# - flaky_search is statistical: reported as observed rates, excluded from counts
# - (answer_directly, output) is test-dependent by design: the math rubric can
#   pass with a correct ungrounded answer; grounded rubrics fail on fabrication
EXPECTED_BROKEN = {
    "none": set(),
    "vague_answers": {"output"},
    "answer_directly": {"process", "evidence"},
    "flaky_search": set(),
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default=str(PROJECT_ROOT / "eval/results.md"))
    args = parser.parse_args()

    lines = [
        "# Harness meta-evaluation",
        "",
        "Per-scorer pass rates for the demo suite under each injected failure mode.",
        "",
        "| Mode | Test | process | evidence | output | verdict |",
        "|---|---|---|---|---|---|",
    ]
    should_break_cells = broken_detected = 0
    healthy_cells = healthy_clean = 0

    for mode in MODES:
        os.environ["DEMO_FAILURE_MODE"] = mode
        result = run_suite(SUITE)
        for t in result.tests:
            cells = []
            for scorer in ("process", "evidence", "output"):
                rate = t.scorer_pass_rates.get(scorer)
                cells.append("n/a" if rate is None else f"{rate:.2f}")
                if rate is None or mode == "flaky_search":
                    continue
                if mode == "answer_directly" and scorer == "output":
                    continue
                if scorer in EXPECTED_BROKEN[mode]:
                    should_break_cells += 1
                    if rate < 1.0:
                        broken_detected += 1
                else:
                    healthy_cells += 1
                    if rate == 1.0:
                        healthy_clean += 1
            verdict = "PASS" if t.passed else "FAIL"
            lines.append(
                f"| {mode} | {t.name} | {cells[0]} | {cells[1]} | {cells[2]} | {verdict} |"
            )

    lines += [
        "",
        f"- Injected-failure detection: {broken_detected}/{should_break_cells} "
        "broken stages flagged",
        f"- Isolation: {healthy_clean}/{healthy_cells} healthy stages stayed green",
        "- flaky_search reported as observed pass rates (statistical, run-dependent)",
        "- answer_directly output is test-dependent by design: a correct ungrounded "
        "answer can pass the math rubric while grounded rubrics fail on fabrication",
    ]
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines) + "\n")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
