"""
Three independent scorers: process, evidence, output.
"""
import json
import os
import re
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

DEFAULT_JUDGE_MODEL = "gpt-5.6-sol"
GROQ_BASE_URL = "https://api.groq.com/openai/v1"

_STOPWORDS = {
    "a", "about", "above", "absent", "agent", "all", "and", "answer", "be",
    "by", "cite", "clearly", "equal", "every", "from", "given", "grounded",
    "include", "invent", "must", "not", "of", "or", "reference", "retrieved",
    "rubric", "satisfies", "say", "score", "state", "study", "text", "that",
    "the", "to", "verdict", "well", "with",
}

def _has_openai_credentials() -> bool:
    return bool(os.environ.get("OPENAI_API_KEY") or os.environ.get("OPENAI_ADMIN_KEY"))

def _judge_provider() -> str:
    return os.environ.get("AGENT_HARNESS_JUDGE_PROVIDER", "openai").lower()

def _judge_api_key() -> str | None:
    if _judge_provider() == "groq":
        return os.environ.get("GROQ_API_KEY")
    return os.environ.get("OPENAI_API_KEY") or os.environ.get("OPENAI_ADMIN_KEY")

def _judge_base_url() -> str | None:
    if _judge_provider() == "groq":
        return GROQ_BASE_URL
    return os.environ.get("OPENAI_BASE_URL") or os.environ.get("OPENAI_API_BASE")

def _has_live_judge_credentials() -> bool:
    return bool(_judge_api_key())

def _tokens(text: str) -> set[str]:
    return {
        t
        for t in re.findall(r"[a-z0-9]+", text.lower())
        if len(t) > 1 and t not in _STOPWORDS
    }

def _numeric_tokens(text: str) -> set[str]:
    nums = set()
    for raw in re.findall(r"\d+(?:\.\d+)?", text):
        value = float(raw)
        nums.add(str(int(value)) if value.is_integer() else str(value))
    return nums

def _lexical_relevance(task: str, evidence: str) -> float:
    task_tokens = _tokens(task)
    evidence_tokens = _tokens(evidence)
    if not task_tokens or not evidence_tokens:
        return 0.0
    return len(task_tokens & evidence_tokens) / len(task_tokens)

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
    forbidden = [t for t in actual if t in exp.forbidden_tools]
    failed_calls = [tc.name for tc in trace.tool_calls if not tc.succeeded]

    passed = score == 1.0 and not forbidden
    if forbidden:
        reason = (
            f"forbidden tool(s) called: {forbidden}; "
            f"actual sequence: {actual}"
        )
    elif passed:
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
            "forbidden_tools": exp.forbidden_tools,
            "forbidden_calls": forbidden,
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
    successful_tools = {call.name for call in trace.tool_calls if call.succeeded and call.output}
    missing_required_tools = [tool for tool in exp.required_tools if tool not in successful_tools]

    if exp.required and not evidence:
        return ScoreResult(
            scorer="evidence",
            passed=False,
            score=0.0,
            reason="agent produced an answer without any successful tool output"
                    "(answered without evidence)",
            details={"evidence_count": 0, "agent_error": trace.error},
        )

    if missing_required_tools:
        matched = len(exp.required_tools) - len(missing_required_tools)
        score = matched / len(exp.required_tools)
        return ScoreResult(
            scorer="evidence",
            passed=False,
            score=score,
            reason=(
                "missing successful evidence from required tool(s): "
                f"{missing_required_tools}"
            ),
            details={
                "evidence_count": len(evidence),
                "required_tools": exp.required_tools,
                "successful_tools": sorted(successful_tools),
                "missing_required_tools": missing_required_tools,
            },
        )
    
    if exp.min_relevance is None:
        return ScoreResult(
            scorer="evidence",
            passed=True,
            score=1.0,
            reason=f"{len(evidence)} evidence chunk(s) gathered before answering",
            details={
                "evidence_count": len(evidence),
                "required_tools": exp.required_tools,
                "successful_tools": sorted(successful_tools),
            },
        )
    
    if embed_fn is None and not _has_openai_credentials():
        sims = [_lexical_relevance(trace.input, chunk) for chunk in evidence]
        best = max(sims) if sims else 0.0
        passed = best >= exp.min_relevance
        return ScoreResult(
            scorer="evidence",
            passed=passed,
            score=best,
            reason=(
                f"best lexical evidence relevance {best:.2f} "
                f"{'meets' if passed else 'below'} threshold {exp.min_relevance}"
            ),
            details={
                "evidence_count": len(evidence),
                "similarities": [round(s, 3) for s in sims],
                "offline_scorer": True,
            },
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

def _score_output_locally(exp: OutputExpectation, trace: Trace, model: str) -> ScoreResult:
    rubric_tokens = _tokens(exp.rubric) | _numeric_tokens(exp.rubric)
    answer_tokens = _tokens(trace.final_answer) | _numeric_tokens(trace.final_answer)

    if not rubric_tokens:
        score = 1.0 if trace.final_answer.strip() else 0.0
        matched = set()
    else:
        matched = rubric_tokens & answer_tokens
        score = len(matched) / len(rubric_tokens)

    passed = score >= exp.threshold
    return ScoreResult(
        scorer="output",
        passed=passed,
        score=score,
        reason=(
            f"offline heuristic matched {len(matched)}/{len(rubric_tokens)} "
            "rubric keyword(s)"
        ),
        details={
            "threshold": exp.threshold,
            "judge_model": model,
            "offline_scorer": True,
            "expected_terms": sorted(rubric_tokens),
            "matched_terms": sorted(matched),
        },
    )

def score_output(
    exp: OutputExpectation,
    trace: Trace,
    client: Any = None,
    model: str = DEFAULT_JUDGE_MODEL,
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
    
    if client is None and not _has_live_judge_credentials():
        return _score_output_locally(exp, trace, model)

    if client is None:
        from openai import OpenAI
        client = OpenAI(api_key=_judge_api_key(), base_url=_judge_base_url())

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
