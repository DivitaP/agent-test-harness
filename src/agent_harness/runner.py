"""
Loading a target graph and executing a single traced run
"""
import importlib
import time
from typing import Any

from langchain_core.messages import HumanMessage
from agent_harness.trace import Trace, TraceCollector

def load_target(target: str) -> Any:
    """
    Resolve 'package.module:attribute' to a compiled LangGraph.
    """
    try:
        module_path, attr = target.split(":")
    except ValueError:
        raise ValueError(
            f"target must be in the form 'package.module:attribute', got '{target}'"
        )
    module = importlib.import_module(module_path)
    try:
        return getattr(module, attr)
    except AttributeError:
        raise ValueError(
            f"no attribute '{attr}' in module '{module_path}'"
        )

def run_single(app: Any, task_input: str) -> Trace:
    """
    Invoke the graph once with tracing attached. Never raises -
    agent failures are recorded on the trace so scorers can report them.
    """

    collector = TraceCollector()
    collector.trace.input = task_input
    start = time.monotonic()

    try:
        result = app.invoke(
            { "messages": [HumanMessage(content=task_input)]},
            config={"callbacks": [collector]},
        )
        collector.trace.final_answer = _extract_final_answer(result)
    except Exception as e: # noqa: BLE001 — deliberate: harness must survive agent crashes
        collector.trace.error = f"{type(e).__name__}: {e}"

    collector.trace.duration_ms = (time.monotonic() - start) * 1000
    return collector.trace

def _extract_final_answer(result: Any) -> str:
    """
    Pull the final answer from common LangGraph result shapes.
    """

    if isinstance(result, dict) and "messages" in result and result["messages"]:
        last = result["messages"][-1]
        return str(getattr(last, "content", last))
    
    return str(result)
