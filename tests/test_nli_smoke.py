import pytest

pytest.importorskip("torch", reason="torch is required for NLIScorer tests")

from backend.nli import NLIScorer


class _FakeBackend:
    def score(self, pairs):
        return [0.42 for _ in pairs]


def test_nli_scores_float(monkeypatch):
    monkeypatch.setattr(NLIScorer, "_load_backend", lambda self: _FakeBackend())
    scorer = NLIScorer(model_name="dummy")
    assert abs(scorer.score("premise", "hypothesis") - 0.42) < 1e-6
    batch = scorer.score_batch([("a", "b"), ("c", "d")])
    assert batch == [0.42, 0.42]
