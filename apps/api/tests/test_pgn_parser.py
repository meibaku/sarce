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


def game(white_result, black_result, pgn_result=None):
    header = f'[Result "{pgn_result}"]\n' if pgn_result else ""
    return {**SAMPLE_GAME, "pgn": f'{header}1. e4 e5 *', "white": {**SAMPLE_GAME["white"], "result": white_result}, "black": {**SAMPLE_GAME["black"], "result": black_result}}


class TestResults:
    """Chess.com's per-player codes say how *that* player did; the PGN header wins when present."""

    def test_white_resigned_or_timed_out_is_a_black_win(self):
        # Before the fix these read as White wins.
        for code in ("resigned", "timeout", "abandoned"):
            assert parse_chess_com_game(game(code, "win"), "tal_fan")["result"] == "loss"
            assert parse_chess_com_game(game(code, "win"), "opponent1")["result"] == "win"

    def test_draw_codes_are_draws(self):
        for code in ("agreed", "repetition", "stalemate", "insufficient", "50move", "timevsinsufficient"):
            assert parse_chess_com_game(game(code, code), "tal_fan")["result"] == "draw"

    def test_the_pgn_result_header_is_the_source_of_truth(self):
        assert parse_chess_com_game(game("resigned", "win", "0-1"), "opponent1")["result"] == "win"
        assert parse_chess_com_game(game("win", "timeout", "1-0"), "tal_fan")["result"] == "win"
        assert parse_chess_com_game(game("agreed", "agreed", "1/2-1/2"), "opponent1")["result"] == "draw"
