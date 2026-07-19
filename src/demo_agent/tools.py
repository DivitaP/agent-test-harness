"""
Demo agent tools
search_studies gains injectable flakiness via 
DEMO_FAILURE_MODE=flaky_search (simulates a flaky upstream index)
"""

import ast
import operator
import os
import random

from langchain_core.tools import tool
from demo_agent.corpus import STUDIES

@tool
def search_studies(query: str) -> str:
    """
    Search the study corpus by topic keywords.
    Returns matching study IDs and titles.
    """

    if os.environ.get("DEMO_FAILURE_MODE") == "flaky_search" and random.random() < 0.4:
        raise RuntimeError("search index timeout")
    
    words = {w.lower().strip(".,?") for w in query.split()}
    scored = []

    for sid, doc in STUDIES.items():
        haystack = f"{doc['title']} {doc['text']}".lower()
        score = sum(1 for w in words if len(w) > 3 and w in haystack)

        if score:
            scored.append((score, sid, doc["title"]))

    if not scored:
        return "No matching studies found"
    
    scored.sort(reverse=True)

    return "\n".join(f"{sid}: {title}" for _, sid, title in scored[:3])

@tool
def get_study_details(study_id: str) -> str:
    """
    fetch the full text of a study by its ID, for example 'T123'
    """
    doc = STUDIES.get(study_id.strip().upper())
    if doc is None:
        return f"Study '{study_id} not found'"
    
    return f"{doc['title']}\n\n{doc['text']}"

_OPS = {ast.Add: operator.add, ast.Sub: operator.sub,
        ast.Mult: operator.mul, ast.Div: operator.truediv}

def _eval_node(node: ast.AST) -> float:
    """
    Tiny AST walker: numbers and + - * / only.
    Safe construction, anything else (names, calls, imports) raises
    """

    if isinstance(node, ast.Expression):
        return _eval_node(node.body)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _OPS:
        return _OPS[type(node.op)](_eval_node(node.left), _eval_node(node.right))
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        return -_eval_node(node.operand)
    raise ValueError("unsupported expression element")

@tool
def calculator(expression: str) -> str:
    """
    Evaluate a basic arithmetic expression like '0.15 * 240'
    """
    return str(_eval_node(ast.parse(expression, mode="eval")))