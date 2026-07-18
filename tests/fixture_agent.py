"""Deterministic LangGraph fixtures (no LLM) shared across tests."""
from typing import Annotated, TypedDict

from langchain_core.messages import AIMessage, AnyMessage
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages


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


def _make_graph(tools_in_order):
    """Graph with one node per tool call, executed sequentially."""
    g = StateGraph(State)

    def make_node(t):
        def node(state: State, config: RunnableConfig):
            query = state["messages"][0].content
            out = t.invoke(
                {"query": query} if "query" in t.args else {"text": query},
                config,  # config passthrough: callbacks fire
            )
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


app = _make_graph([retrieve_docs, summarize])
failing_app = _make_graph([broken_tool])


def _direct_graph():
    """Answers directly with zero tool calls: the 'no evidence' scenario."""
    g = StateGraph(State)

    def node(state: State, config: RunnableConfig):
        return {"messages": [AIMessage(content="42. No sources were needed.")]}

    g.add_node("answer", node)
    g.set_entry_point("answer")
    g.add_edge("answer", END)
    return g.compile()


direct_answer_app = _direct_graph()