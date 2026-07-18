"""
Aggregated result models: rim -> test -> suite -> report.
"""
from pydantic import BaseModel, computed_field

from agent_harness.scorers import ScoreResult
from agent_harness.trace import Trace

class RunResult(BaseModel):
    run_index: int
    passed: bool
    scores: list[ScoreResult]
    trace: Trace # full trace kept: the extension's trace panel reads this

class TestResult(BaseModel):
    name: str
    passed: bool
    pass_rate: float
    min_pass_rate: float
    scorer_pass_rates: dict[str, float] # e.g. {"process": 1.0, "evidence": 0.5}
    runs: list[RunResult]

class SuiteResult(BaseModel):
    suite_path: str
    target: str
    duration_ms: float
    tests: list[TestResult]

    @computed_field
    @property
    def passed_count(self) -> int:
        return sum(t.passed for t in self.tests)
    
    @computed_field
    @property
    def failed_count(self) -> int:
        return len(self.tests) - self.passed_count
    
    @computed_field
    @property
    def passed(self) -> bool:
        return self.failed_count == 0
    
class Report(BaseModel):
    suites: list[SuiteResult]

    @computed_field
    @property
    def total_tests(self) -> int:
        return sum(len(s.tests) for s in self.suites)
    
    @computed_field
    @property
    def passed_tests(self) -> int:
        return sum(s.passed_count for s in self.suites)
    
    @computed_field
    @property
    def all_passed(self) -> bool:
        return all(s.passed for s in self.suites)