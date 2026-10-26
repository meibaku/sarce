"""Operational guarantees for the fixed-snapshot Maia backfill."""

import pytest

from scripts.backfill_human_probs import execute


class FlakyQuery:
    def __init__(self, failures: int):
        self.failures = failures
        self.calls = 0

    def execute(self):
        self.calls += 1
        if self.calls <= self.failures:
            raise RuntimeError("transient database pressure")
        return "done"


def test_execute_retries_then_returns(monkeypatch):
    monkeypatch.setattr("scripts.backfill_human_probs.time.sleep", lambda _seconds: None)
    query = FlakyQuery(2)
    assert execute(query) == "done"
    assert query.calls == 3


def test_execute_reraises_after_the_budget(monkeypatch):
    monkeypatch.setattr("scripts.backfill_human_probs.time.sleep", lambda _seconds: None)
    with pytest.raises(RuntimeError, match="transient"):
        execute(FlakyQuery(5), attempts=3)
