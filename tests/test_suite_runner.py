import pytest
from pathlib import Path

from agent_harness.schema import AgentTest
from agent_harness.suite_runner import run_suite, run_test
from tests.fixture_agent import app, failing_app
from tests.helpers import FakeJudge, FlakyJudge

FIXTURES = Path(__file__).parent / "fixtures"


def test_suite_happy_path():
    result = run_suite(FIXTURES / "sample.agent-test.yaml", judge_client=FakeJudge(0.9))
    assert result.passed
    t = result.tests[0]
    assert t.pass_rate == 1.0
    assert t.scorer_pass_rates == {"process": 1.0, "evidence": 1.0, "output": 1.0}
    assert len(t.runs) == 2


def test_scorer_breakdown_isolates_failing_stage():
    result = run_suite(FIXTURES / "failing.agent-test.yaml", judge_client=FakeJudge(0.9))
    t = result.tests[0]
    assert not t.passed
    assert t.scorer_pass_rates["evidence"] == 0.0   # the broken stage
    assert t.scorer_pass_rates["output"] == 1.0     # the answer itself was fine
    assert "process" not in t.scorer_pass_rates     # not configured for this test


def test_flaky_pass_rate_measured():
    test = AgentTest(
        name="flaky", input="q",
        output={"rubric": "any"},
        runs=4, min_pass_rate=0.5,
    )
    r = run_test(app, test, judge_client=FlakyJudge())
    assert r.pass_rate == 0.5
    assert r.passed          # 0.5 >= 0.5


def test_flaky_fails_strict_threshold():
    test = AgentTest(name="flaky", input="q", output={"rubric": "any"}, runs=4)
    r = run_test(app, test, judge_client=FlakyJudge())
    assert r.pass_rate == 0.5
    assert not r.passed      # default min_pass_rate is 1.0


def test_agent_crash_is_failed_run_not_harness_crash():
    test = AgentTest(name="crash", input="q", output={"rubric": "any"})
    r = run_test(failing_app, test, judge_client=FakeJudge(0.9))
    assert not r.passed
    out = next(s for s in r.runs[0].scores if s.scorer == "output")
    assert "agent run failed" in out.reason


def test_run_suite_filter_no_match():
    with pytest.raises(ValueError, match="no tests match"):
        run_suite(FIXTURES / "sample.agent-test.yaml",
                  judge_client=FakeJudge(0.9), test_filter=["nope"])
        
