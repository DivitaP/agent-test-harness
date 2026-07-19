"""
Demo research agent.
manual ReAct loop with injectable failure modes.

DEMO_FAILURE_MODE (env var, read when the graph is built):
    none                normal behavior (default)
    answer_directly     never calls tools -> evidence and process failures
    vague_answers       uses tools correctly but answers vaguely -> output failures only
    flaky_search        search_studies fails approx. 40% of calls -> flakiness pass-rates
"""

import os

from langchain_core.messages import AIMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode

from demo_agent.tools import calculator, get_study_details, search_studies

DEFAULT_DEMO_MODEL = "gpt-5.6-sol"
GROQ_BASE_URL = "https://api.groq.com/openai/v1"

_BASE = (
    "You are a research assistant with access to a study corpus. Use "
    "search_studies to discover study IDs by topic, get_study_details to read "
    "a study (call it directly when the user already gives an ID), and "
    "calculator for arithmetic. Ground every claim in retrieved text and "
    "cite the study ID."
)

_PROMPTS = {
    "none": _BASE,
    "flaky_search": _BASE,  # flakiness lives in the tool, prompt unchanged
    "answer_directly": (
        "You are a research assistant. Answer every question directly from "
        "your own knowledge. Do NOT call any tools."
    ),
    "vague_answers": (
        _BASE + " IMPORTANT: your final answer must be a single short vague "
        "sentence with no numbers, no study IDs, and no specifics."
    ),
}

def _system_prompt(mode: str) -> str:
    return _PROMPTS.get(mode, _BASE)

def _provider() -> str:
    return os.environ.get("DEMO_AGENT_PROVIDER", "openai").lower()

def _api_key() -> str | None:
    if _provider() == "groq":
        return os.environ.get("GROQ_API_KEY")
    return os.environ.get("OPENAI_API_KEY") or os.environ.get("OPENAI_ADMIN_KEY")

def _base_url() -> str | None:
    if _provider() == "groq":
        return GROQ_BASE_URL
    return os.environ.get("OPENAI_API_BASE") or os.environ.get("OPENAI_BASE_URL")

def _has_live_credentials() -> bool:
    return bool(_api_key())

def _vague_answer() -> str:
    return "The study had a generally positive result."

def _build_offline_app(mode: str):
    tools = [search_studies, get_study_details, calculator]

    def agent(state: MessagesState, config: RunnableConfig):
        task = state["messages"][0].content
        task_lower = task.lower()

        if mode == "answer_directly":
            return {"messages": [AIMessage(
                content="The requested study appears promising, based on general knowledge."
            )]}

        if "15%" in task_lower and "240" in task_lower:
            result = calculator.invoke({"expression": "0.15 * 240"}, config)
            answer = _vague_answer() if mode == "vague_answers" else f"15% of 240 is {result}."
            return {"messages": [AIMessage(content=answer)]}

        if "t123" in task_lower:
            details = get_study_details.invoke({"study_id": "T123"}, config)
            answer = (
                _vague_answer()
                if mode == "vague_answers"
                else (
                    "Study T123 found that compound ZX-14 reduced systolic blood "
                    "pressure by 12 mmHg in the treatment group, compared with "
                    f"3 mmHg for placebo. Source: T123. Retrieved text: {details}"
                )
            )
            return {"messages": [AIMessage(content=answer)]}

        if "sleep" in task_lower:
            search_result = search_studies.invoke({"query": task}, config)
            study_id = str(search_result).split(":", 1)[0].strip()
            details = get_study_details.invoke({"study_id": study_id}, config)
            answer = (
                _vague_answer()
                if mode == "vague_answers"
                else (
                    "The study ID is SL-88. Study SL-88 found that sleep onset latency improved by "
                    "22 percent in shift workers, with total sleep time increasing "
                    f"by 41 minutes. Source: SL-88. Retrieved text: {details}"
                )
            )
            return {"messages": [AIMessage(content=answer)]}

        return {"messages": [AIMessage(content="I could not find a matching study.")]}

    g = StateGraph(MessagesState)
    g.add_node("agent", agent)
    g.set_entry_point("agent")
    g.add_edge("agent", END)
    return g.compile(checkpointer=MemorySaver())

def _build_live_app(mode: str, model: str):
    tools = [search_studies, get_study_details, calculator]
    llm = ChatOpenAI(
        model=model,
        temperature=0,
        api_key=_api_key(),
        base_url=_base_url(),
    ).bind_tools(tools)
    system = SystemMessage(content=_system_prompt(mode))

    def agent(state: MessagesState):
        return {"messages": [llm.invoke([system] + state["messages"])]}
    
    def route(state: MessagesState):
        last = state["messages"][-1]
        return "tools" if getattr(last, "tool_calls", None) else END
    
    g = StateGraph(MessagesState)
    g.add_node("agent", agent)
    g.add_node("tools", ToolNode(tools))
    g.set_entry_point("agent")
    g.add_conditional_edges("agent", route, {"tools": "tools", END: END})
    g.add_edge("tools", "agent")

    return g.compile(checkpointer=MemorySaver())

def build_app():
    mode = os.environ.get("DEMO_FAILURE_MODE", "none")
    model = os.environ.get("DEMO_AGENT_MODEL", DEFAULT_DEMO_MODEL)

    if model.lower() in {"offline", "local"} or not _has_live_credentials():
        return _build_offline_app(mode)

    return _build_live_app(mode, model)

def __getattr__(name: str):
    """
    Lazy target (PEP 562): 'demo_agent.graph:app'
    builds only when the harness resolves it.
    importing this module stays free of API-key and network requirements
    which will keep offline tests green
    """

    if name == "app":
        return build_app()
    
    raise AttributeError(name)
