"""Your traps (app/services/traps_set.py): positions you steer into where opponents go wrong next move."""

from unittest.mock import patch

import chess
from fastapi.testclient import TestClient

from app.main import app
from app.services import traps_set

client = TestClient(app)

# You are White; after 4.Bc4 the opponent sometimes plays the natural-looking but losing 4...Nf6?? (in this test).
FELL = "1. e4 e5 2. Nf3 Nc6 3. d4 exd4 4. Bc4 Nf6 *"
HELD = "1. e4 e5 2. Nf3 Nc6 3. d4 exd4 4. Bc4 Bc5 *"


def game(pgn):
    return {"pgn": pgn, "user_color": "white"}


def test_reached_positions_counts_your_moves_and_their_replies():
    reached = traps_set.reached_positions([game(FELL)] * 3 + [game(HELD)] * 2)
    after_bc4 = next(v for v in reached.values() if v["move"] == "Bc4")
    assert after_bc4["seen"] == 5 and after_bc4["replies"]["g8f6"] == 3 and after_bc4["replies"]["f8c5"] == 2
    assert after_bc4["line"].endswith("d4 exd4 Bc4")
    # Positions after the opponent's moves are never counted.
    board = chess.Board(after_bc4["fen"])
    assert board.turn == chess.BLACK


def test_score_trap_counts_replies_far_below_the_best():
    entry = traps_set.reached_positions([game(FELL)] * 3 + [game(HELD)] * 2)
    after_bc4 = next(v for v in entry.values() if v["move"] == "Bc4")
    lines = [{"move_uci": "f8c5", "cp": 20, "mate": None}, {"move_uci": "g8f6", "cp": -180, "mate": None}]
    found = traps_set.score_trap(after_bc4, lines)
    assert found == {"caught": 3, "rate": 0.6, "gain_cp": 200, "slip": "Nf6", "defence": "Bc5"}
    # A reply within TRAP_CP of the best is not a trap.
    assert traps_set.score_trap(after_bc4, [{"move_uci": "f8c5", "cp": 20, "mate": None}, {"move_uci": "g8f6", "cp": -60, "mate": None}]) is None


@patch("app.routers.users.traps_set_service.get", return_value=[{"move": "Bc4"}])
def test_get_route(mock_get):
    assert client.get("/users/traps-set").json() == {"traps": [{"move": "Bc4"}], "building": False}


def test_likely_rate_shrinks_small_samples():
    # Ranked by the Wilson lower bound: 30 of 40 beats a perfect 3 of 3 (review F7).
    assert traps_set.likely_rate(30, 40) > traps_set.likely_rate(3, 3)
    assert traps_set.likely_rate(0, 0) == 0.0
