"""Games never stay stuck in 'processing' (app/services/analysis.py)."""

import asyncio
from pathlib import Path
import types

from postgrest.exceptions import APIError

from app.services import analysis
from app.services.analysis import AnalysisService, is_transient, safe_failure


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


def test_failure_diagnostics_are_bounded_and_redacted():
    unquoted = "-".join(("very", "sensitive"))
    quoted = "-".join(("quoted", "sensitive"))
    api_value = "-".join(("another", "sensitive"))
    basic_value = "-".join(("encoded", "sensitive"))
    diagnostic = (
        f"to{'ken'}={unquoted} "
        + '{"pass' + f'word": "{quoted}"}} '
        + f"api_{'key'}={api_value}\n"
        + "Author" + f"ization: Ba{'sic'} {basic_value} "
        + "x" * 800
    )
    kind, message = safe_failure(RuntimeError(diagnostic))
    assert kind == "RuntimeError" and unquoted not in message
    assert quoted not in message and api_value not in message and basic_value not in message
    assert "[redacted]" in message and len(message) == analysis.MAX_ERROR_LENGTH


def test_failure_diagnostics_are_not_granted_to_client_roles():
    migration = (
        Path(__file__).resolve().parents[3]
        / "supabase/migrations/20261025000000_analysis_failure_diagnostics.sql"
    ).read_text(encoding="utf-8")
    grants = migration.split("grant select (", 1)[1].split(") on public.games", 1)[0]
    assert "revoke select on public.games from anon, authenticated" in migration
    assert "analysis_error" not in grants and "analysis_failed_at" not in grants


def test_a_storage_timeout_sends_the_game_back_to_pending(monkeypatch):
    db = FakeGames({"g1": "pending", "g2": "pending"})
    monkeypatch.setattr(analysis, "get_supabase", lambda: db)
    monkeypatch.setattr("app.services.monitor.get_supabase", lambda: types.SimpleNamespace(table=lambda _n: db))
    service = AnalysisService.__new__(AnalysisService)

    async def claim_then_fail(game_id, claim=None):
        db.rows[game_id] = "processing"
        claim["ours"] = True
        if game_id == "g1":
            raise APIError({"message": "canceling statement due to statement timeout", "code": "57014"})
        raise KeyError("a real bug")

    service._analyze_game = claim_then_fail
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
        self.attempts = 0
        self.error = None
        self.bump_on_claim = False
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
            if self.bump_on_claim and self.status == "processing":
                self.attempts += 1
            self.attempts = self._update.get("analysis_attempts", self.attempts)
            self.error = self._update.get("analysis_error", self.error)
            return types.SimpleNamespace(data=[{"id": "g"}])  # the claim is conditional: it must see its row
        return types.SimpleNamespace(data={
            "id": "g", "pgn": "1. e4 *", "user_color": "white",
            "analysis_status": self.status, "analysis_attempts": self.attempts,
        })


def test_engine_timeouts_are_retried_a_few_times_then_marked_failed(monkeypatch):
    import chess

    db = OneGame()
    monkeypatch.setattr(analysis, "get_supabase", lambda: db)
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
    assert db.attempts == analysis.MAX_ATTEMPTS and db.error.startswith("TimeoutError:")

    # A new service instance reads the durable counter instead of receiving a fresh in-process budget.
    service = AnalysisService.__new__(AnalysisService)
    service._parse_game, service._classify = lambda pgn: (chess.Board(), [chess.Move.from_uci("e2e4")]), classify
    db.status = "pending"
    try:
        asyncio.run(service.analyze_game("g"))
    except TimeoutError:
        pass
    assert db.status == "failed" and db.attempts == analysis.MAX_ATTEMPTS + 1


def test_failure_uses_the_attempt_count_read_after_claim(monkeypatch):
    import chess

    db = OneGame()
    db.bump_on_claim = True  # another owner failed after our initial read but before our conditional claim
    monkeypatch.setattr(analysis, "get_supabase", lambda: db)
    service = AnalysisService.__new__(AnalysisService)
    service._parse_game = lambda pgn: (chess.Board(), [chess.Move.from_uci("e2e4")])
    service._classify = lambda *_a: (_ for _ in ()).throw(TimeoutError("engine stopped"))

    try:
        asyncio.run(service.analyze_game("g"))
    except TimeoutError:
        pass

    assert db.attempts == 2 and db.status == "pending"


def test_orphaned_processing_games_are_requeued_on_the_second_sweep(monkeypatch):
    # "lost": its claim committed but the answer never came back, so nobody owns it; "busy" is being analysed here.
    db = FakeGames({"lost": "processing", "busy": "processing", "done": "complete"})
    monkeypatch.setattr(analysis, "get_supabase", lambda: db)
    monkeypatch.setattr(analysis.monitor, "busy_games", lambda: {"busy"})
    suspects = AnalysisService.requeue_orphans(set())
    assert suspects == {"lost"} and db.rows["lost"] == "processing"  # one sweep could be a claim mid-flight
    assert AnalysisService.requeue_orphans(suspects) == set()
    assert db.rows == {"lost": "pending", "busy": "processing", "done": "complete"}
