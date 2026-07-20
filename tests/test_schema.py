from pathlib import Path

import pytest
from pydantic import ValidationError

from agent_harness.schema import (
    AgentTest,
    TestSuite as Suite,
    load_suite,
    discover_suites,
)

EXAMPLES = Path(__file__).parent.parent / "examples"


def test_loads_valid_suite():
    suite = load_suite(EXAMPLES / "research_agent.agent-test.yaml")
    assert suite.target == "demo_agent.graph:app"
    assert len(suite.tests) == 2
    assert suite.tests[0].runs == 3
    assert suite.tests[0].process.expected_tools == ["retrieve_docs", "summarize"]


def test_defaults_applied():
    suite = load_suite(EXAMPLES / "research_agent.agent-test.yaml")
    t = suite.tests[1]
    assert t.runs == 1                      # default
    assert t.output.threshold == 0.7        # default
    assert t.process.strict_order is True   # default


def test_rejects_empty_suite():
    with pytest.raises(ValidationError, match="at least one test"):
        Suite.model_validate({"target": "x:y", "tests": []})


def test_rejects_blank_name():
    with pytest.raises(ValidationError, match="blank"):
        AgentTest.model_validate({
            "name": "  ",
            "input": "hi",
            "output": {"rubric": "anything"},
        })


def test_output_is_mandatory():
    with pytest.raises(ValidationError):
        AgentTest.model_validate({"name": "t", "input": "hi"})


def test_discover_finds_example():
    found = discover_suites(EXAMPLES)
    assert "research_agent.agent-test.yaml" in {path.name for path in found}

def test_min_pass_rate_default():
    t = AgentTest.model_validate({"name": "t", "input": "q", "output": {"rubric": "r"}})
    assert t.min_pass_rate == 1.0
