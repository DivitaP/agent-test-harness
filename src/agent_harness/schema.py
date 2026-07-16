"""Schema module for agent_harness.

Schema for .agent-test.yaml files.
"""
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field, field_validator

class ProcessExpectation(BaseModel):
    """Expected tool-call trajectory. Ordered subsequence match with partial credit."""
    expected_tools: list[str] = Field(
        description="Tool names expected to be called, in order."
    )
    strict_order: bool = Field(
        default=True,
        description="IF True, tools must appear in this relative order (gaps allowed)",
    )

class EvidenceExpectation(BaseModel):
    """
    Checks that the agent gathered grounding before answering.
    """
    required: bool = Field(
        default=True,
        description="IF True, agent must have non-empty tool output before final answer",
    )
    min_relevance: float | None = Field(
        default=None, ge=0.0, le=1.0,
        description="Optional embedding-similarity threshold between task and evidence."
    )

class OutputExpectation(BaseModel):
    """
    Natural language rubric judged by an LLM.
    """
    rubric: str = Field(
        description="Plain english criteria the final answer must satisfy."
    )
    threshold: float = Field(
        default=0.7, ge=0.0, le=1.0,
        description="Minimum judge score to pass",
    )

class AgentTest(BaseModel):
    """
    One test case
    """
    name: str
    input: str = Field(description="Task/prompt sent to the agent.")
    process: ProcessExpectation | None = None
    evidence: EvidenceExpectation | None = None
    output: OutputExpectation
    runs: int = Field(default=1, ge=1, le=20, description="Repeat count for flakiness.")

    @field_validator("name")
    @classmethod
    def name_not_blank(cls, v:str) -> str:
        if not v.strip():
            raise ValueError("test name cannot be blank")
        return v
    
class TestSuite(BaseModel):
    """
    Top level of a .agent-test.yaml file.
    """
    target: str = Field(
        description="Import path to the compiled LangGraph, e.g. 'demo_agent.graph:app'."
    )
    tests: list[AgentTest]

    @field_validator("tests")
    @classmethod
    def at_least_one_test(cls, v:list[AgentTest]) -> list[AgentTest]:
        if not v:
            raise ValueError("suite must contain at least one test")
        return v

def load_suite(path: str | Path) -> TestSuite:
    """Parse and validate a .agent-test.yaml file."""
    path = Path(path)
    with path.open() as f:
        raw = yaml.safe_load(f)
    return TestSuite.model_validate(raw)

def discover_suites(root: str | Path) -> list[Path]:
    """Find all .agent-test.yaml files under root."""
    return sorted(Path(root).rglob("*.agent-test.yaml"))