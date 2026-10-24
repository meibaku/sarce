"""Chaos map (app/services/chaos_map.py): frequent opening positions and the sound move that asks the most."""

from unittest.mock import patch

import chess
from fastapi.testclient import TestClient

from app.main import app
from app.services import chaos_map

client = TestClient(app)

SICILIAN = "1. e4 c5 2. Nf3 d6 3. d4 cxd4 4. Nxd4 Nf6 5. Nc3 a6 *"
ALAPIN = "1. e4 c5 2. c3 d5 3. exd5 Qxd5 4. d4 Nf6 *"


def game(pgn, color="black", rating=1180):
    return {"pgn": pgn, "user_color": color, "opponent_rating": rating}


def test_opening_positions_counts_your_turns_and_opponent_predictability():
    games = [game(SICILIAN)] * 6 + [game(ALAPIN)] * 2
    positions = chaos_map.opening_positions(games)
    assert positions, "the Sicilian positions come up six times"
    assert all(p["seen"] >= chaos_map.MIN_SEEN for p in positions)
    # Black to move in every position (the player is Black), none before MIN_PLY.
    assert all(chess.Board(p["fen"]).turn == chess.BLACK for p in positions)
    after_nf3 = next(p for p in positions if p["line"] == "e4 c5 Nf3")
    assert after_nf3["usual"] == "d7d6" and after_nf3["usualCount"] == 6
    # After 1.e4 c5 White played Nf3 in 6 of 8 games.
    assert after_nf3["predictability"] == 0.75
    # Ties on `seen` go to the deeper position.
    assert len(positions[0]["line"]) >= len(positions[1]["line"])


def test_rare_positions_are_left_out():
    assert chaos_map.opening_positions([game(SICILIAN)] * (chaos_map.MIN_SEEN - 1)) == []


class FakeEngine:
    """Two sound moves for the side to move; replies decide how hard each one is."""

    def analyse(self, board, nodes, multipv):
        legal = [m.uci() for m in board.legal_moves]
        if not board.move_stack:  # the position under test (built from its FEN)
            return [{"move_uci": "d7d6", "ep": 0.50}, {"move_uci": "e7e5", "ep": 0.46}, {"move_uci": "g7g5", "ep": 0.20}]
        if board.peek().uci() == "e7e5":
            # One safe reply among many: a 1200 player often misses it.
            return [{"move_uci": legal[0], "ep": 0.6}] + [{"move_uci": u, "ep": 0.2} for u in legal[1:8]]
        return [{"move_uci": u, "ep": 0.5} for u in legal[:8]]


class FlatModel:
    def move_probs(self, board, elo):
        legal = [m.uci() for m in board.legal_moves]
        return {u: 1 / len(legal) for u in legal}


def test_chaos_move_prefers_the_sound_move_that_is_hard_to_answer():
    board = chess.Board()
    for san in ["e4", "c5", "Nf3"]:
        board.push_san(san)
    found = chaos_map.chaos_move({"fen": board.fen(), "usual": "d7d6"}, FakeEngine(), FlatModel(), 1200)
    assert found["chaos"]["san"] == "e5" and found["chaos"]["pFail"] > 0.8
    # After d6 every reply holds: nothing at stake, so nothing to miss.
    assert found["usual"]["san"] == "d6" and found["usual"]["stake"] == 0
    # g5 is unsound (0.30 below best), so never suggested.
    assert found["chaos"]["epLoss"] <= chaos_map.SOUND_TOL


def test_opponent_rung_is_the_nearest_ladder_step():
    # Chess.com rapid 1150 and 1290 are about Lichess 1,540 and 1,650 on the model's scale (review F1).
    assert chaos_map.opponent_rung([game(SICILIAN, rating=1150), game(SICILIAN, rating=1290)]) == 1600
    assert chaos_map.opponent_rung([{**game(SICILIAN, rating=1150), "source": "lichess"}]) == 1200
    assert chaos_map.opponent_rung([{"pgn": ""}]) == 1200


@patch("app.routers.users.chaos_map_service.get", return_value=[{"line": "e4 c5 Nf3"}])
def test_get_route_returns_positions(mock_get):
    res = client.get("/users/chaos-map")
    assert res.status_code == 200 and res.json() == {"positions": [{"line": "e4 c5 Nf3"}], "building": False}


@patch("app.routers.users.chaos_map_service.build", return_value={"positions": 0, "elo": 1200})
def test_post_route_rebuilds_in_the_background(mock_build):
    res = client.post("/users/chaos-map")
    assert res.status_code == 200 and res.json() == {"building": True}
    mock_build.assert_called_once()


def mapped(gain, same=False):
    return {
        "key": f"k{gain}", "fen": chess.STARTING_FEN, "line": "e4 e5 Bc4 Nf6 Nf3 Nc6", "seen": 54, "same": same,
        "usual": {"san": "d4", "problem": 0.2}, "chaos": {"san": "Ng5", "problem": 0.2 + gain},
    }


def test_drills_only_where_the_chaos_move_clearly_asks_more():
    items = chaos_map.drill_items([mapped(0.01), mapped(0.17), mapped(0.05), mapped(0.3, same=True)])
    assert [i["key"] for i in items] == ["chaos:k0.17", "chaos:k0.05"]  # biggest gain first; tiny gains and "same" skipped
    assert items[0]["source"] == chaos_map.CHAOS_DRILL and items[0]["answer"] == "Ng5"
    assert "_gain" not in items[0]


def test_chaos_drill_feedback_names_the_harder_move():
    from app.services.train import check_move

    board = chess.Board()
    for san in ["e4", "e5", "Bc4", "Nf6", "Nf3", "Nc6"]:
        board.push_san(san)
    hit = check_move(board.fen(), "f3g5", "Ng5", False, chaos_drill=True)
    assert hit["matched"] and "opponent" in hit["line"]
    calm = check_move(board.fen(), "d2d4", "Ng5", False, loss=lambda b, m: 0.0, chaos_drill=True)
    assert calm["sound"] and "Ng5 asks more" in calm["line"]
