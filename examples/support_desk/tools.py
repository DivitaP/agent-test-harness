"""Tools for the support demo, including the injectable flaky dependency."""

import json
import os
import random

from langchain_core.tools import tool

from support_desk.data import ORDERS, REFUND_POLICY


@tool
def lookup_order(order_id: str) -> str:
    """Look up one fictional order, accepting IDs with or without a leading #."""
    if (
        os.environ.get("DEMO_FAILURE_MODE") == "flaky_lookup"
        and random.random() < 0.4
    ):
        raise RuntimeError("order database timeout")
    normalized = order_id.strip().lstrip("#")
    order = ORDERS.get(normalized)
    if order is None:
        return f"Order {normalized} not found"
    return json.dumps({"order_id": normalized, **order}, sort_keys=True)


@tool
def check_refund_policy(question: str) -> str:
    """Return the complete policy so the agent can ground eligibility claims."""
    return REFUND_POLICY


@tool
def issue_refund(order_id: str, amount: float) -> str:
    """Issue a fictional refund only for a known order; eligibility is agent-tested."""
    normalized = order_id.strip().lstrip("#")
    if normalized not in ORDERS:
        return f"Refund refused: order {normalized} not found"
    return f"Refund issued for order {normalized}: ${amount:.2f}."
