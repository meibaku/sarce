"""Sarce bots (app/services/bots.py): stateless play, move choice and the chaos-in-reverse score."""

import random
from unittest.mock import patch

import chess
from fastapi.testclient import TestClient

from app.main import app
from app.services import bots

client = TestClient(app)


class FakeEngine:
    """Lines for the side to move: e2e4 best, d2d4 close, a2a3 much worse."""

    def __init__(self, lines):
        self.lines = lines

    def analyse(self, board, nodes, multipv):
        legal = {m.uci() for m in board.legal_moves}
        return [l for l in self.lines if l["move_uci"] in legal][:multipv] or [
            {"move_uci": next(iter(legal)), "ep": 0.5}
        ]


class FlatModel:
    def move_probs(self, board, elo):
        legal = [m.uci() for m in board.legal_moves]
        return {u: 1 / len(legal) for u in legal}


LINES = [{"move_uci": "e2e4", "ep": 0.55}, {"move_uci": "d2d4", "ep": 0.52}, {"move_uci": "a2a3", "ep": 0.30}]


def test_status_and_payload():
    mate = chess.Board("7k/5KQ1/8/8/8/8/8/8 b - - 0 1")
    assert bots.status(mate) == "checkmate"
    start = bots.position_payload(chess.Board())
    assert start["status"] == "ongoing" and "e2e4" in start["legal"] and start["turn"] == "white"


def test_p_fail_and_stake():
    replies = [{"move_uci": "a", "ep": 0.6}, {"move_uci": "b", "ep": 0.58}, {"move_uci": "c", "ep": 0.2}]
    p_fail, stake = bots.p_fail_and_stake(replies, {"a": 0.2, "b": 0.1, "c": 0.7})
    assert round(p_fail, 2) == 0.70 and round(stake, 2) == 0.40


def test_defender_only_plays_sound_moves():
    rng = random.Random(1)
    picks = {bots.choose("defender", chess.Board(), 1600, FakeEngine(LINES), FlatModel(), rng).uci() for _ in range(30)}
    assert picks <= {"e2e4", "d2d4"} and "a2a3" not in picks


def test_move_route_rejects_illegal_moves_and_unknown_bots():
    assert client.post("/play/move", json={"fen": chess.STARTING_FEN, "uci": "e2e5"}).status_code == 422
    assert client.post("/play/move", json={"fen": chess.STARTING_FEN, "uci": "e2e4", "bot": "gm"}).status_code == 422


def test_move_route_applies_player_then_bot():
    with patch("app.services.bots.StockfishEngine") as engine_cls, patch("app.services.bots.get_human_model", return_value=FlatModel()):
        engine_cls.return_value.__enter__.return_value = FakeEngine([{"move_uci": "e7e5", "ep": 0.5}])
        from app.routers.play import bot_service

        bot_service._engine = None
        res = client.post("/play/move", json={"fen": chess.STARTING_FEN, "uci": "e2e4", "bot": "defender"})
        bot_service._engine = None
    data = res.json()
    assert res.status_code == 200 and data["playerSan"] == "e4" and data["botSan"] == "e5"
    assert data["turn"] == "white" and data["status"] == "ongoing"


def test_player_move_without_reply_skips_the_engine():
    with patch("app.services.bots.StockfishEngine") as engine_cls:
        res = client.post("/play/move", json={"fen": chess.STARTING_FEN, "uci": "e2e4", "reply": False})
    assert res.json()["turn"] == "black" and res.json()["botSan"] is None
    engine_cls.assert_not_called()


def test_bot_game_pgn_replays_with_clocks():
    from datetime import datetime, timezone

    import chess.pgn
    import io
    from app.services.bots import bot_game_pgn

    pgn = bot_game_pgn(["e2e4", "e7e5", "d1h5"], "draw", "tal", [179000, 178000, 170500], datetime(2026, 10, 19, tzinfo=timezone.utc))
    game = chess.pgn.read_game(io.StringIO(pgn))
    assert game.headers["Result"] == "1/2-1/2" and game.headers["Black"] == "Tal-style attacker"
    assert [n.clock() for n in game.mainline()] == [179.0, 178.0, 170.5]


def test_bot_game_pgn_rejects_illegal_moves():
    from datetime import datetime, timezone

    import pytest
    from app.services.bots import bot_game_pgn

    with pytest.raises(ValueError):
        bot_game_pgn(["e2e5"], "win", "tal", None, datetime.now(timezone.utc))
