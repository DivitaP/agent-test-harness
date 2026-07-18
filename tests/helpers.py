"""Shared test doubles."""
import json
from types import SimpleNamespace


class FakeJudge:
    """Stands in for the OpenAI client; returns a fixed verdict."""

    def __init__(self, score: float = 1.0, reasoning: str = "ok"):
        payload = json.dumps({"score": score, "reasoning": reasoning})
        create = lambda **kw: SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=payload))]
        )
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=create))


class FlakyJudge:
    """Alternates score 1.0, 0.0, 1.0, ... across calls: deterministic flakiness."""

    def __init__(self):
        self._n = 0
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

    def _create(self, **kw):
        score = 1.0 if self._n % 2 == 0 else 0.0
        self._n += 1
        payload = json.dumps({"score": score, "reasoning": f"call {self._n}"})
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=payload))]
        )