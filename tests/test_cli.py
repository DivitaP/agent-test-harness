import json
from pathlib import Path

from agent_harness.cli import main
from tests.helpers import FakeJudge

FIXTURES = Path(__file__).parent / "fixtures"


def test_cli_json_report_and_exit_zero(capsys):
    code = main(
        ["run", str(FIXTURES / "sample.agent-test.yaml"), "--json"],
        judge_client=FakeJudge(0.9),
    )
    report = json.loads(capsys.readouterr().out)
    assert code == 0
    assert report["all_passed"] is True
    assert report["total_tests"] == 1
    assert report["suites"][0]["tests"][0]["scorer_pass_rates"]["process"] == 1.0


def test_cli_exit_one_on_failure(capsys):
    code = main(
        ["run", str(FIXTURES / "failing.agent-test.yaml")],
        judge_client=FakeJudge(0.9),
    )
    out = capsys.readouterr().out
    assert code == 1
    assert "FAIL" in out
    assert "without evidence" in out   # failure reason surfaced in console


def test_cli_directory_discovery_aggregates(capsys):
    code = main(["run", str(FIXTURES), "--json"], judge_client=FakeJudge(0.9))
    report = json.loads(capsys.readouterr().out)
    assert code == 1                   # the failing suite is in the directory
    assert len(report["suites"]) == 2
    assert report["passed_tests"] == 1


def test_cli_bad_path_exit_two(capsys):
    code = main(["run", "does/not/exist"])
    assert code == 2
    assert "not found" in capsys.readouterr().err


def test_cli_writes_output_file(tmp_path, capsys):
    out_file = tmp_path / "report.json"
    code = main(
        ["run", str(FIXTURES / "sample.agent-test.yaml"), "--json",
         "--output", str(out_file)],
        judge_client=FakeJudge(0.9),
    )
    capsys.readouterr()
    assert code == 0
    assert json.loads(out_file.read_text())["all_passed"] is True