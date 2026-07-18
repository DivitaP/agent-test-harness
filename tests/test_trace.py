import pytest

from agent_harness.runner import load_target, run_single
from tests.fixture_agent import _make_graph, app, broken_tool


# --- tests -----------------------------------------------------------

def test_captures_tool_sequence_in_order():
    trace = run_single(app, "study T123 findings")
    assert trace.tool_sequence == ["retrieve_docs", "summarize"]
    assert trace.error is None


def test_captures_tool_io_and_timing():
    trace = run_single(app, "study T123 findings")
    first = trace.tool_calls[0]
    assert "study T123" in first.input
    assert "3 documents" in first.output
    assert first.duration_ms is not None and first.duration_ms >= 0
    assert first.succeeded


def test_captures_final_answer():
    trace = run_single(app, "study T123 findings")
    assert trace.final_answer.startswith("Summary of")


def test_evidence_property_collects_outputs():
    trace = run_single(app, "study T123 findings")
    assert len(trace.evidence) == 2


def test_tool_error_recorded_not_raised():
    failing = _make_graph([broken_tool])
    trace = run_single(failing, "anything")
    assert trace.tool_calls[0].error is not None
    assert "upstream service down" in trace.tool_calls[0].error
    assert not trace.tool_calls[0].succeeded
    # graph itself crashed after tool error -> recorded on trace, not raised
    assert trace.error is not None


def test_load_target_resolves_this_module():
    graph = load_target("tests.test_trace:app")
    assert graph is app


def test_load_target_bad_format():
    with pytest.raises(ValueError, match="package.module:attribute"):
        load_target("no-colon-here")


def test_load_target_missing_attr():
    with pytest.raises(ValueError, match="no attribute"):
        load_target("tests.test_trace:nonexistent")