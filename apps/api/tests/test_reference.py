"""Tests for reference-player benchmark helpers."""

import chess.pgn

from app.services.reference import infer_player_color


class TestInferPlayerColor:
    def test_detects_tal_as_black(self):
        game = chess.pgn.Game()
        game.headers["White"] = "Bent Larsen"
        game.headers["Black"] = "Mikhail Tal"

        assert infer_player_color(game, "Mikhail Tal") == "black"

    def test_detects_tal_as_white(self):
        game = chess.pgn.Game()
        game.headers["White"] = "Mikhail Tal"
        game.headers["Black"] = "Bent Larsen"

        assert infer_player_color(game, "Mikhail Tal") == "white"

    def test_detects_last_name_first_black_header(self):
        game = chess.pgn.Game()
        game.headers["White"] = "Bent Larsen"
        game.headers["Black"] = "Tal, Mikhail N."

        assert infer_player_color(game, "Mikhail Tal") == "black"


class _NoRowQuery:
    """supabase-py's maybe_single().execute() returns None, not an empty result, for no row."""

    def __init__(self, results):
        self._results = results

    def __getattr__(self, _name):
        return lambda *args, **kwargs: self

    def execute(self):
        return self._results.pop(0)


class TestTalBenchmark:
    def test_player_without_a_benchmark_row_is_pending_not_a_crash(self, monkeypatch):
        import asyncio
        import types

        from app.services import reference

        player = types.SimpleNamespace(data={"id": "p1", "name": "Mikhail Tal", "games_sampled": 0})
        query = _NoRowQuery([player, None])
        monkeypatch.setattr(reference, "get_supabase", lambda: types.SimpleNamespace(table=lambda _t: query))
        bench = asyncio.run(reference.ReferenceService().get_tal_benchmark())
        assert bench["status"] == "pending" and bench["playerName"] == "Mikhail Tal"
