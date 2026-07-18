"""
Three independent scorers: process, evidence, output.
"""
import json
from collections import Counter
from typing import Any, Callable, Literal

from pydantic import BaseModel, Field

from agent_harness.schema import (
    EvidenceExpectation,
    OutputExpectation,
    ProcessExpectation,
)
from agent_harness.trace import Trace

class ScoreResult(BaseModel):
    scorer: Literal["process", "evidence", "output"]
    passed: bool
    score: float = Field(ge=0.0, le=1.0)
    reason: str
    details: dict[str, Any] = Field(default_factory=dict)

# ------------ process -------------------------------------------------------

def _lcs_length(expected: list[str], actual: list[str]) -> int:
    """
    Longest common subsequence - max number of expected tools that
    appear in `actual` in the same relative order
    """
    m, n = len(expected), len(actual)
    dp = [[0] * (n+1) for _ in range(m+1)]
    for i in range(1, m+1):
        for j in range(1, n+1):
            if expected[i-1] == actual[j-1]:
                dp[i][j] = dp[i-1][j-1] + 1
            else:
                dp[i][j] = max(dp[i-1][j], dp[i][j-1])
    return dp[m][n]

def score_process(exp: ProcessExpectation, trace: Trace) -> ScoreResult:
    actual = trace.tool_sequence
    expected = exp.expected_tools

    if exp.strict_order:
        matched = _lcs_length(expected, actual)
    else:
        matched = sum((Counter(expected) & Counter(actual)).values())

    score = matched / len(expected)
    unexpected = [t for t in actual if t not in expected]
    failed_calls = [tc.name for tc in trace.tool_calls if not tc.succeeded]

    passed = score == 1.0
    if passed:
        reason = f"all {len(expected)} expected tools called in order"
    else:
        reason = f"matched {matched}/{len(expected)} expected tools; actual sequence: {actual}"

    return ScoreResult(
        scorer="process",
        passed=passed,
        score=score,
        reason=reason,
        details={
            "expected": expected,
            "actual": actual,
            "unexpected_tools": unexpected,
            "failed_tool_calls": failed_calls,
            "agent_error": trace.error,
        },
    )

# ------------ evidence -------------------------------------------------------

def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x,y in zip(a,b))
    na = sum(x * x for x in a) ** 0.5
    nb = sum(y * y for y in b) ** 0.5
    return dot / (na * nb) if na and nb else 0.0

def _openai_embed(texts: list[str]) -> list[list[float]]:
    from openai import OpenAI
    resp = OpenAI().embeddings.create(model="text-embedding-3-small", input=texts)
    return [d.embedding for d in resp.data]

EmbedFn = Callable[[list[str]], list[list[float]]]

def score_evidence(
        exp: EvidenceExpectation,
        trace: Trace,
        embed_fn: EmbedFn | None = None,
) -> ScoreResult:
    evidence = trace.evidence

    if exp.required and not evidence:
        return ScoreResult(
            scorer="evidence",
            passed=False,
            score=0.0,
            reason="agent produced an answer without any successful tool output"
                    "(answered without evidence)",
            details={"evidence_count": 0, "agent_error": trace.error},
        )
    
    if exp.min_relevance is None:
        return ScoreResult(
            scorer="evidence",
            passed=True,
            score=1.0,
            reason=f"{len(evidence)} evidence chunk(s) gathered before answering",
            details={"evidence_count": len(evidence)},
        )
    
    # relevance check: best cosine similarity between task and any chunk
    embed = embed_fn or _openai_embed
    vectors = embed([trace.input] + evidence)
    task_vec, chunk_vecs = vectors[0], vectors[1:]
    sims = [_cosine(task_vec, cv) for cv in chunk_vecs]
    best = max(sims)
    passed = best >= exp.min_relevance

    return ScoreResult(
        scorer="evidence",
        passed=passed,
        score=best,
        reason=(
            f"best evidence relevance {best:.2f} "
            f"{'meets' if passed else 'below'} threshold {exp.min_relevance}"
        ),
        details={"evidence_count": len(evidence), "similarities": [round(s, 3) for s in sims]},
    )

# ------------ output -------------------------------------------------------

JUDGE_SYSTEM = (
    "You are a strict test judge for AI agent outputs. Score how well the "
    "answer satisfies the rubric, from 0.0 (complete failure) to 1.0 (fully "
    "satisfies). Penalize fabricated facts. Respond with JSON only: "
    '{"score": <float 0..1>, "reasoning": "<one short paragraph>"}'
)

def score_output(
    exp: OutputExpectation,
    trace: Trace,
    client: Any = None,
    model: str = "gpt-5.6",
) -> ScoreResult:
    
    # auto fail conditions where no judge call needed

    if trace.error:
        return ScoreResult(
            scorer="output", 
            passed=False, 
            score=0.0,
            reason=f"agent run failed before producing an answer: {trace.error}",
        )
    
    if not trace.final_answer.strip():
        return ScoreResult(
            scorer="output",
            passed=False,
            score=0.0,
            reason=f"agent produced an empty final answer",
        )
    
    if client is None:
        from openai import OpenAI
        client = OpenAI()

    user_msg = (
        f"TASK GIVEN TO AGENT:\n{trace.input}\n\n"
        f"RUBRIC:\n{exp.rubric}\n\n"
        f"AGENT'S FINAL ANSWER:\n{trace.final_answer}"
    )
    resp = client.chat.completions.create(
        model=model,
        temperature=0,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": JUDGE_SYSTEM},
            {"role": "user", "content": user_msg},
        ]
    )

    raw = resp.choices[0].message.content
    try:
        verdict = json.loads(raw)
        score = max(0.0, min(1.0, float(verdict["score"])))
        reasoning = str(verdict.get("reasoning", ""))
    except (json.JSONDecodeError, KeyError, TypeError, ValueError) as e:
        return ScoreResult(
            scorer="output",
            passed=False,
            score=0.0,
            reason=f"judge returned unparseable verdict: {e}",
            details={"raw_verdict": raw},
        )
    
    passed = score >= exp.threshold
    return ScoreResult(
        scorer="output",
        passed=passed,
        score=score,
        reason=reasoning,
        details={"threshold": exp.threshold, "judge_model": model},
    )
