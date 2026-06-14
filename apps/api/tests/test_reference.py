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
