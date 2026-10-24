"""Opponent-aware chaos (app/services/opponent_chaos.py, plan 3.7)."""

from collections import Counter

from app.services import opponent_chaos as oc

PGN = '[Event "?"]\n\n1. e4 e5 2. Nf3 Nc6 3. Bc4 Nd4 4. Nxe5 Qg5 *'
PGN2 = '[Event "?"]\n\n1. e4 e5 2. Nf3 Nc6 3. Bc4 Nf6 4. Ng5 d5 *'


def test_frequent_positions_with_the_player_to_move():
    games = [{"pgn": PGN, "user_color": "black"}, {"pgn": PGN2, "user_color": "black"}]
    pos = oc.frequent_positions(games)
    assert len(pos) == 1  # after 1.e4 e5 2.Nf3 Nc6 3.Bc4, seen twice with Black to move
    assert pos[0]["line"] == "e4 e5 Nf3 Nc6 Bc4" and pos[0]["replies"] == Counter({"c6d4": 1, "g8f6": 1})


class FakeEngine:
    def analyse(self, board, nodes, multipv):
        return [{"move_uci": "g8f6", "ep": 0.5}, {"move_uci": "f8c5", "ep": 0.48}, {"move_uci": "c6d4", "ep": 0.3}]


class FakeModel:
    def move_probs(self, board, elo):
        return {"g8f6": 0.4, "f8c5": 0.2, "c6d4": 0.4}


def test_score_counts_replies_that_gave_ground():
    entry = {"fen": "r1bqkbnr/pppp1ppp/2n5/4p3/2B1P3/5N2/PPPP1PPP/RNBQK2R b KQkq - 3 3", "line": "e4 e5 Nf3 Nc6 Bc4", "seen": 3, "replies": Counter({"c6d4": 2, "g8f6": 1})}
    s = oc.score_position(entry, FakeEngine(), FakeModel(), 1200)
    assert s["wrong"] == 2 and s["lostEp"] == 0.2 and s["slip"] == "Nd4" and s["best"] == "Nf6" and s["elo"] == 1200


def test_their_level_is_their_opponents_converted():
    games = [{"time_control": "600", "opponent_rating": 1255}, {"time_control": "600", "opponent_rating": 1255}]
    assert oc.their_level(games, "chess_com") == 1600
    assert oc.their_level([], "lichess") == 1500
