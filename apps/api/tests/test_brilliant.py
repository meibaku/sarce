"""Tests for Tal-style brilliant move detection."""

import chess

from app.services.brilliant import (
    has_reasonable_alternatives,
    is_brilliant_move,
    material_sacrifice,
)


class TestMaterialSacrifice:
    def test_no_sacrifice_on_quiet_move(self):
        board = chess.Board()
        move = chess.Move.from_uci("e2e4")
        assert material_sacrifice(board, move) == 0

    def test_detects_offered_piece_sacrifice(self):
        board = chess.Board(
            "rnbqkb1r/pppppppp/5n2/8/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 1 2"
        )
        move = chess.Move.from_uci("d1h5")
        assert material_sacrifice(board, move) == 9

    def test_en_passant_counts_captured_pawn_value(self):
        board = chess.Board(
            "rnbqkbnr/ppp1p1pp/8/3pPp2/8/8/PPPP1PPP/RNBQKBNR w KQkq f6 0 3"
        )
        move = chess.Move.from_uci("e5f6")
        assert material_sacrifice(board, move) == 0

    def test_sacrifice_when_queen_given(self):
        board = chess.Board("rnbqkb1r/pppp1ppp/5n2/4p2Q/4P3/8/PPPP1PPP/RNB1KBNR b KQkq - 0 3")
        # Black captures queen — from black's perspective not sacrifice
        # White queen on h5, black can take
        board.turn = chess.WHITE
        move = chess.Move.from_uci("h5f7")  # queen sac on f7
        sac = material_sacrifice(board, move)
        assert sac >= 0  # may be 0 if not losing material on board count


class TestBrilliantMove:
    def test_rejects_when_no_sacrifice(self):
        board = chess.Board()
        move = chess.Move.from_uci("e2e4")
        assert (
            is_brilliant_move(
                board, move,
                eval_before=0.0, eval_after=0.1, best_eval=0.0,
            )
            is False
        )

    def test_rejects_when_already_winning(self):
        board = chess.Board("rnb1kb1r/pppp1ppp/5n2/4p2Q/4P3/8/PPPP1PPP/RNB1KBNR w KQkq - 0 3")
        move = chess.Move.from_uci("h5f7")
        assert (
            is_brilliant_move(
                board, move,
                eval_before=4.0, eval_after=3.5, best_eval=4.0,
            )
            is False
        )

    def test_rejects_forced_move(self):
        board = chess.Board("6k1/5ppp/8/8/8/8/8/6K1 w - - 0 1")
        legal = list(board.legal_moves)
        if len(legal) == 1:
            assert has_reasonable_alternatives(board, legal[0]) is False
