from typing import Annotated, TypedDict

import pytest
from langchain_core.messages import AIMessage, AnyMessage
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages

from agent_harness.runner import load_target, run_single


# --- deterministic fixture graph (no LLM) ---------------------------

@tool
def retrieve_docs(query: str) -> str:
    """Fetch documents for a query."""
    return f"3 documents about: {query}"


@tool
def summarize(text: str) -> str:
    """Summarize text."""
    return f"Summary of [{text[:20]}...]"


@tool
def broken_tool(query: str) -> str:
    """Always fails."""
    raise RuntimeError("upstream service down")


class State(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]


def _make_graph(tools_in_order, fail=False):
    """Graph with one node per tool call, executed sequentially."""
    g = StateGraph(State)

    def make_node(t):
        def node(state: State, config: RunnableConfig):
            query = state["messages"][0].content
            out = t.invoke({"query": query} if "query" in t.args else {"text": query},
                           config)  # <-- config passthrough = callbacks fire
            return {"messages": [AIMessage(content=str(out))]}
        return node

    prev = None
    for t in tools_in_order:
        g.add_node(t.name, make_node(t))
        if prev is None:
            g.set_entry_point(t.name)
        else:
            g.add_edge(prev, t.name)
        prev = t.name
    g.add_edge(prev, END)
    return g.compile()


# expose a target for load_target test
app = _make_graph([retrieve_docs, summarize])


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