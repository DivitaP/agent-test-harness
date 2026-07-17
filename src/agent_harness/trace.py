"""
Trace models + callback collector for LangGraph runs.
"""
import time
import uuid
from typing import Any

from langchain_core.callbacks import BaseCallbackHandler
from pydantic import BaseModel, Field

class ToolCall(BaseModel):
    """
    One tool invocation observed during a run.
    """
    name: str
    input: str
    output: str | None = None
    error: str | None = None
    started_at: float
    duration_ms: float | None = None


    @property
    def succeeded(self) -> bool:
        return self.error is None
    

class Trace(BaseModel):
    """
    Everything recorded from a single agent run.
    """
    run_id: str = Field(default_factory=lambda: uuid.uuid4().hex[:8])
    input: str = ""
    tool_calls: list[ToolCall] = Field(default_factory=list)
    final_answer: str = ""
    error: str | None = None
    duration_ms: float | None = None

    @property
    def tool_sequence(self) -> list[str]:
        """
        ordered tool names - what the process scorer matched against
        """
        return [tc.name for tc in self.tool_calls]
    
    @property
    def evidence(self) -> list[str]:
        """
        successful tool outputs - what the evidence scorer inspects
        """
        return [tc.output for tc in self.tool_calls if tc.output]
    
class TraceCollector(BaseCallbackHandler):
    """
    Langchain callback handler that records tool events into a Trace.

    Langgraph propagates config (including callbacks) to every node and 
    tool invocation, so attaching this at graph.invoke() captures the 
    whole run without touching agent code.
    """

    def __init__(self) -> None:
        super().__init__()
        self.trace = Trace()
        # run_id -> ToolCall, because tools can run concurrently
        self._pending: dict[str, ToolCall] = {}

    # -------- tool events --------
    def on_tool_start(
            self, serialized: dict[str, Any], input_str: str, *,
            run_id: uuid.UUID, **kwargs: Any,
    ) -> None:
        call = ToolCall(
            name=serialized.get("name", "unknown"),
            input = input_str,
            started_at = time.monotonic(),
        )
        self._pending[str(run_id)] = call
        self.trace.tool_calls.append(call) # appending at start to preserve order

    def on_tool_end(self, output: Any, *, run_id: uuid.UUID, **kwargs: Any) -> None:
        call = self._pending.pop(str(run_id), None)
        if call:
            # ToolMessage objects carry .content; raw returns dont
            call.output = str(getattr(output, "content", output))
            call.duration_ms = (time.monotonic() - call.started_at) * 1000

    def on_tool_error(self, error: BaseException, *, run_id: uuid.UUID, **kwargs: Any) -> None:
        call = self._pending.pop(str(run_id), None)
        if call:
            call.error = f"{type(error).__name__}: {error}"
            call.duration_ms = (time.monotonic() - call.started_at) * 1000
