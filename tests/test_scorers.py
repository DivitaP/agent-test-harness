import json
from types import SimpleNamespace

from agent_harness.schema import (
    EvidenceExpectation,
    OutputExpectation,
    ProcessExpectation,
)
from agent_harness.scorers import score_evidence, score_output, score_process
from agent_harness.trace import ToolCall, Trace


def make_trace(tools=(), final="an answer", error=None, task="find X"):
    calls = [
        ToolCall(name=n, input="q", output=f"result of {n}", started_at=0.0)
        for n in tools
    ]
    return Trace(input=task, tool_calls=calls, final_answer=final, error=error)


# ---------------------------------------------------------------- process

def test_process_perfect_match():
    exp = ProcessExpectation(expected_tools=["retrieve_docs", "summarize"])
    r = score_process(exp, make_trace(["retrieve_docs", "summarize"]))
    assert r.passed and r.score == 1.0


def test_process_partial_credit():
    exp = ProcessExpectation(expected_tools=["retrieve_docs", "summarize"])
    r = score_process(exp, make_trace(["summarize"]))
    assert not r.passed
    assert r.score == 0.5


def test_process_order_violation_costs_credit():
    exp = ProcessExpectation(expected_tools=["retrieve_docs", "summarize"])
    r = score_process(exp, make_trace(["summarize", "retrieve_docs"]))
    assert r.score == 0.5  # LCS: only one can match in order


def test_process_unordered_mode():
    exp = ProcessExpectation(
        expected_tools=["retrieve_docs", "summarize"], strict_order=False
    )
    r = score_process(exp, make_trace(["summarize", "retrieve_docs"]))
    assert r.passed and r.score == 1.0


def test_process_extra_tools_reported_not_penalized():
    exp = ProcessExpectation(expected_tools=["retrieve_docs"])
    r = score_process(exp, make_trace(["calculator", "retrieve_docs"]))
    assert r.passed
    assert r.details["unexpected_tools"] == ["calculator"]


def test_process_empty_actual():
    exp = ProcessExpectation(expected_tools=["retrieve_docs"])
    r = score_process(exp, make_trace([]))
    assert not r.passed and r.score == 0.0


# --------------------------------------------------------------- evidence

def test_evidence_present_passes():
    r = score_evidence(EvidenceExpectation(required=True), make_trace(["retrieve_docs"]))
    assert r.passed


def test_evidence_missing_fails():
    r = score_evidence(EvidenceExpectation(required=True), make_trace([]))
    assert not r.passed
    assert "without evidence" in r.reason


def test_evidence_relevance_with_fake_embeddings():
    exp = EvidenceExpectation(required=True, min_relevance=0.8)
    trace = make_trace(["retrieve_docs"], task="find X")

    def fake_embed(texts):
        # task and evidence identical vectors -> similarity 1.0
        return [[1.0, 0.0] for _ in texts]

    r = score_evidence(exp, trace, embed_fn=fake_embed)
    assert r.passed and r.score == 1.0


def test_evidence_relevance_below_threshold():
    exp = EvidenceExpectation(required=True, min_relevance=0.9)
    trace = make_trace(["retrieve_docs"])

    def fake_embed(texts):
        return [[1.0, 0.0]] + [[0.0, 1.0]] * (len(texts) - 1)  # orthogonal

    r = score_evidence(exp, trace, embed_fn=fake_embed)
    assert not r.passed and r.score == 0.0


# ----------------------------------------------------------------- output

class FakeJudge:
    """Mimics openai client surface: client.chat.completions.create(...)"""
    def __init__(self, payload: str):
        self._payload = payload
        create = lambda **kw: SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=self._payload))]
        )
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=create))


def test_output_pass_above_threshold():
    exp = OutputExpectation(rubric="mentions X", threshold=0.7)
    judge = FakeJudge(json.dumps({"score": 0.9, "reasoning": "mentions X clearly"}))
    r = score_output(exp, make_trace(["t"]), client=judge)
    assert r.passed and r.score == 0.9


def test_output_fail_below_threshold():
    exp = OutputExpectation(rubric="mentions X", threshold=0.7)
    judge = FakeJudge(json.dumps({"score": 0.4, "reasoning": "vague"}))
    r = score_output(exp, make_trace(["t"]), client=judge)
    assert not r.passed


def test_output_autofails_on_agent_crash():
    exp = OutputExpectation(rubric="anything")
    r = score_output(exp, make_trace(error="RuntimeError: boom"), client=FakeJudge("{}"))
    assert not r.passed and "agent run failed" in r.reason


def test_output_autofails_on_empty_answer():
    exp = OutputExpectation(rubric="anything")
    r = score_output(exp, make_trace(final="  "), client=FakeJudge("{}"))
    assert not r.passed and "empty" in r.reason


def test_output_handles_garbage_judge_response():
    exp = OutputExpectation(rubric="anything")
    r = score_output(exp, make_trace(["t"]), client=FakeJudge("not json at all"))
    assert not r.passed
    assert "unparseable" in r.reason