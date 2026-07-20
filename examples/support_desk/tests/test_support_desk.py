import pytest

from support_desk.graph import _system_prompt
from support_desk.tools import check_refund_policy, issue_refund, lookup_order


def test_lookup_found_and_hash_stripped():
    result = lookup_order.invoke({"order_id": "#4412"})
    assert '"order_id": "4412"' in result
    assert "68.0" in result


def test_lookup_not_found():
    assert "not found" in lookup_order.invoke({"order_id": "#0000"})


def test_policy_tool_returns_policy():
    assert "store credit only" in check_refund_policy.invoke({"question": "undamaged"})


def test_refund_refuses_unknown_order():
    assert "refused" in issue_refund.invoke({"order_id": "#0000", "amount": 12})


def test_flaky_lookup_raises_when_patched(monkeypatch):
    monkeypatch.setenv("DEMO_FAILURE_MODE", "flaky_lookup")
    monkeypatch.setattr("support_desk.tools.random.random", lambda: 0.1)
    with pytest.raises(RuntimeError, match="order database timeout"):
        lookup_order.invoke({"order_id": "7810"})


def test_flaky_lookup_off_by_default(monkeypatch):
    monkeypatch.delenv("DEMO_FAILURE_MODE", raising=False)
    monkeypatch.setattr("support_desk.tools.random.random", lambda: 0.1)
    assert "7810" in lookup_order.invoke({"order_id": "7810"})


def test_prompt_selection_by_mode():
    assert "check_refund_policy" in _system_prompt("none")
    assert "order 4412" in _system_prompt("skip_policy")
    assert "generic sentence" in _system_prompt("vague_answers")
    assert _system_prompt("unknown") == _system_prompt("none")
