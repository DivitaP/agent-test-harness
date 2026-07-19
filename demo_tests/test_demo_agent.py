import pytest

from demo_agent.graph import _system_prompt
from demo_agent.tools import calculator, get_study_details, search_studies


def test_search_ranks_sleep_study_first():
    out = search_studies.invoke({"query": "sleep quality in shift workers"})
    assert out.splitlines()[0].startswith("SL-88")


def test_search_no_match():
    out = search_studies.invoke({"query": "zzzz qqqq"})
    assert "No matching studies" in out


def test_details_found_and_id_normalized():
    out = get_study_details.invoke({"study_id": " t123 "})
    assert "12 mmHg" in out


def test_details_not_found():
    out = get_study_details.invoke({"study_id": "X999"})
    assert "not found" in out


def test_calculator_basic():
    assert calculator.invoke({"expression": "0.15 * 240"}) == "36.0"


def test_calculator_rejects_non_arithmetic():
    with pytest.raises(ValueError):
        calculator.invoke({"expression": "__import__('os')"})


def test_flaky_mode_raises_when_dice_say_so(monkeypatch):
    monkeypatch.setenv("DEMO_FAILURE_MODE", "flaky_search")
    monkeypatch.setattr("demo_agent.tools.random.random", lambda: 0.1)
    with pytest.raises(RuntimeError, match="timeout"):
        search_studies.invoke({"query": "sleep"})


def test_flaky_off_by_default(monkeypatch):
    monkeypatch.delenv("DEMO_FAILURE_MODE", raising=False)
    monkeypatch.setattr("demo_agent.tools.random.random", lambda: 0.1)
    assert "SL-88" in search_studies.invoke({"query": "sleep quality"})


def test_prompt_selection_by_mode():
    assert "Do NOT call any tools" in _system_prompt("answer_directly")
    assert "vague" in _system_prompt("vague_answers")
    assert _system_prompt("unknown") == _system_prompt("none")