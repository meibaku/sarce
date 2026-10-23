"""Games never stay stuck in 'processing' (app/services/analysis.py)."""

import asyncio
import types

from postgrest.exceptions import APIError

from app.services import analysis
from app.services.analysis import AnalysisService, is_transient


class FakeGames:
    """Just enough of supabase-py for a games table held in a dict."""

    def __init__(self, rows):
        self.rows = rows  # id -> status
        self._filters, self._update, self._select = {}, None, False

    def table(self, _name):
        self._filters, self._update, self._select = {}, None, False
        return self

    def select(self, *_a, **_k):
        self._select = True
        return self

    def update(self, values):
        self._update = values
        return self

    def eq(self, col, value):
        self._filters[col] = value
        return self

    def order(self, *_a, **_k):
        return self

    def limit(self, *_a):
        return self

    def execute(self):
        hit = [i for i, st in self.rows.items() if self._filters.get("id", i) == i and self._filters.get("analysis_status", st) == st]
        if self._update:
            for i in hit:
                self.rows[i] = self._update["analysis_status"]
        return types.SimpleNamespace(data=[{"id": i} for i in hit])


def test_transient_errors():
    assert is_transient(APIError({"message": "canceling statement due to statement timeout", "code": "57014"}))
    assert is_transient(TimeoutError())
    assert not is_transient(ValueError("bad pgn"))


def test_a_storage_timeout_sends_the_game_back_to_pending(monkeypatch):
    db = FakeGames({"g1": "pending", "g2": "pending"})
    monkeypatch.setattr(analysis, "get_supabase", lambda: db)
    service = AnalysisService.__new__(AnalysisService)

    async def analyze_game(game_id):
        db.rows[game_id] = "processing"
        if game_id == "g1":
            raise APIError({"message": "canceling statement due to statement timeout", "code": "57014"})
        raise KeyError("a real bug")

    service.analyze_game = analyze_game
    asyncio.run(service.analyze_pending())
    assert db.rows == {"g1": "pending", "g2": "failed"}


def test_startup_requeues_interrupted_games(monkeypatch):
    db = FakeGames({"a": "processing", "b": "complete", "c": "processing"})
    monkeypatch.setattr(analysis, "get_supabase", lambda: db)
    assert AnalysisService.requeue_interrupted() == 2
    assert db.rows == {"a": "pending", "b": "complete", "c": "pending"}


class OneGame:
    """A games table with one row: answers analyze_game's single-row read and records status updates."""

    def __init__(self):
        self.status = "pending"
        self._update = None

    def table(self, _name):
        self._update = None
        return self

    def __getattr__(self, _name):
        return lambda *a, **k: self

    def update(self, values):
        self._update = values
        return self

    def execute(self):
        if self._update:
            self.status = self._update["analysis_status"]
            return types.SimpleNamespace(data=[])
        return types.SimpleNamespace(data={"id": "g", "pgn": "1. e4 *", "user_color": "white"})


def test_engine_timeouts_are_retried_a_few_times_then_marked_failed(monkeypatch):
    import chess

    db = OneGame()
    monkeypatch.setattr(analysis, "get_supabase", lambda: db)
    monkeypatch.setattr(analysis, "_attempts", {})
    service = AnalysisService.__new__(AnalysisService)
    service._parse_game = lambda pgn: (chess.Board(), [chess.Move.from_uci("e2e4")])

    def classify(*_a):
        raise TimeoutError("engine took too long")

    service._classify = classify
    statuses = []
    for _ in range(analysis.MAX_ATTEMPTS):
        try:
            asyncio.run(service.analyze_game("g"))
        except TimeoutError:
            pass
        statuses.append(db.status)
    # Back to the queue twice, then failed: a game that always fails cannot hold a worker forever.
    assert statuses == ["pending"] * (analysis.MAX_ATTEMPTS - 1) + ["failed"]
