"""ReAct Support Desk graph with lazy live-model construction.

The offline graph is intentional: it lets the demo suite and unit tests run
without credentials, while the live path uses Groq when GROQ_API_KEY exists.
"""

import json
import os
from typing import Any

from langchain_core.messages import AIMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode

from support_desk.tools import check_refund_policy, issue_refund, lookup_order

TOOLS = [lookup_order, check_refund_policy, issue_refund]
_BASE_PROMPT = (
    "You are a careful customer-support refund agent. Ground every claim in a "
    "tool result. For a refund request, first call lookup_order, then call "
    "check_refund_policy, then call issue_refund only when the policy permits it. "
    "Cite the order ID, item, amount, and applicable policy condition. Never "
    "promise a timeline other than 5 to 7 business days. Never refund an order "
    "that is still in transit."
)
_PROMPTS = {
    "none": _BASE_PROMPT,
    "flaky_lookup": _BASE_PROMPT,
    "skip_policy": (
        _BASE_PROMPT
        + " For order 4412 only, skip check_refund_policy and issue the full refund "
        "after lookup; still refuse in-transit refunds and use policy for other cases."
    ),
    "vague_answers": (
        _BASE_PROMPT
        + " Use the tools correctly, but make the final answer one generic sentence "
        "with no IDs, amounts, or policy specifics."
    ),
}


def _system_prompt(mode: str) -> str:
    """Select the failure-mode instruction without requiring a model or API key."""
    return _PROMPTS.get(mode, _PROMPTS["none"])


def _order_id(text: str) -> str | None:
    """Extract the demo order ID from a user message."""
    for candidate in ("4412", "7810", "9925"):
        if candidate in text:
            return candidate
    return None


def _offline_answer(mode: str, task: str, config: RunnableConfig) -> dict[str, list[AIMessage]]:
    """Provide a deterministic local simulation for tests and no-key demos."""
    task_lower = task.lower()
    if "policy" in task_lower and not _order_id(task):
        policy = check_refund_policy.invoke({"question": task}, config)
        answer = policy if mode != "vague_answers" else "Your request is covered by our policy."
        return {"messages": [AIMessage(content=answer)]}

    order_id = _order_id(task)
    if order_id is None:
        return {"messages": [AIMessage(content="I could not identify an order number.")]}

    order_raw = lookup_order.invoke({"order_id": order_id}, config)
    order = json.loads(order_raw) if order_raw.startswith("{") else {}
    is_in_transit = order.get("status") == "in-transit"
    skip_policy = mode == "skip_policy" and order_id == "4412"
    if not skip_policy:
        check_refund_policy.invoke({"question": task}, config)

    if is_in_transit:
        answer = (
            "We refuse the refund for order 9925 because it is still in transit. "
            "The policy says in-transit items cannot be refunded until delivered; "
            "do not call this refundable, and do not issue a refund."
        )
    elif order_id == "4412":
        issue_refund.invoke({"order_id": order_id, "amount": 68.00}, config)
        answer = (
            "A full refund of $68.00 has been issued for order 4412, the damaged "
            "brass table lamp. Damaged items qualify within 30 days of delivery. "
            "The refund timeline is 5 to 7 business days."
        )
    else:
        answer = (
            "The item in order 7810 is a wool throw blanket costing $42.50, "
            "delivered in fine condition. It qualifies for store credit only "
            "within 14 days of delivery, not a cash refund."
        )

    if mode == "vague_answers":
        answer = "Your request has been reviewed and handled according to our policy."
    return {"messages": [AIMessage(content=answer)]}


def _build_offline_app(mode: str):
    def agent(state: MessagesState, config: RunnableConfig):
        return _offline_answer(mode, str(state["messages"][0].content), config)

    graph = StateGraph(MessagesState)
    graph.add_node("agent", agent)
    graph.add_node("tools", ToolNode(TOOLS))
    graph.set_entry_point("agent")
    graph.add_conditional_edges(
        "agent",
        lambda state: "tools" if getattr(state["messages"][-1], "tool_calls", None) else END,
        {"tools": "tools", END: END},
    )
    graph.add_edge("tools", "agent")
    return graph.compile(checkpointer=MemorySaver())


def _build_live_app(mode: str):
    from langchain_groq import ChatGroq

    llm = ChatGroq(
        model="llama-3.3-70b-versatile",
        temperature=0,
        api_key=os.environ["GROQ_API_KEY"],
    ).bind_tools(TOOLS)
    system = SystemMessage(content=_system_prompt(mode))

    def agent(state: MessagesState):
        return {"messages": [llm.invoke([system] + state["messages"])]}

    def route(state: MessagesState):
        return "tools" if getattr(state["messages"][-1], "tool_calls", None) else END

    graph = StateGraph(MessagesState)
    graph.add_node("agent", agent)
    graph.add_node("tools", ToolNode(TOOLS))
    graph.set_entry_point("agent")
    graph.add_conditional_edges("agent", route, {"tools": "tools", END: END})
    graph.add_edge("tools", "agent")
    return graph.compile(checkpointer=MemorySaver())


def build_app(render_only: bool = False):
    """Build a fresh graph so changing DEMO_FAILURE_MODE takes effect."""
    mode = os.environ.get("DEMO_FAILURE_MODE", "none")
    if render_only or not os.environ.get("GROQ_API_KEY"):
        return _build_offline_app(mode)
    return _build_live_app(mode)


def __getattr__(name: str) -> Any:
    """Expose app lazily so importing the target never builds a live model."""
    if name == "app":
        return build_app()
    raise AttributeError(name)
