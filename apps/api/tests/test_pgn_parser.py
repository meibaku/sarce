"""Tests for Chess.com PGN parsing."""

from app.services.pgn_parser import parse_chess_com_game


SAMPLE_GAME = {
    "url": "https://chess.com/game/12345",
    "end_time": 1710000000,
    "time_control": "600",
    "pgn": '[Event "Live Chess"]\n1. e4 e5 2. Nf3 *',
    "white": {"username": "tal_fan", "rating": 1500, "result": "win"},
    "black": {"username": "opponent1", "rating": 1480, "result": "checkmated"},
}


class TestParseChessComGame:
    def test_parses_white_user(self):
        result = parse_chess_com_game(SAMPLE_GAME, "tal_fan")
        assert result is not None
        assert result["user_color"] == "white"
        assert result["opponent"] == "opponent1"
        assert result["opponent_rating"] == 1480
        assert result["result"] == "win"
        assert result["external_id"] == "https://chess.com/game/12345"

    def test_parses_black_user(self):
        result = parse_chess_com_game(SAMPLE_GAME, "opponent1")
        assert result is not None
        assert result["user_color"] == "black"
        assert result["result"] == "loss"

    def test_returns_none_without_pgn(self):
        assert parse_chess_com_game({"white": {}, "black": {}}, "x") is None
