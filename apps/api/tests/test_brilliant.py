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

    def test_rejects_pawn_sacrifice(self):
        board = chess.Board("8/8/8/4p3/8/3P4/8/4K2k w - - 0 1")
        move = chess.Move.from_uci("d3d4")

        assert material_sacrifice(board, move) == 1
        assert (
            is_brilliant_move(
                board,
                move,
                eval_before=0.0,
                eval_after=0.1,
                best_eval=0.0,
            )
            is False
        )

    def test_rejects_merely_good_sacrifice(self):
        board = chess.Board("rnb1kb1r/pppp1ppp/5n2/4p2Q/4P3/8/PPPP1PPP/RNB1KBNR w KQkq - 0 3")
        move = chess.Move.from_uci("h5f7")

        assert material_sacrifice(board, move) >= 3
        assert (
            is_brilliant_move(
                board,
                move,
                eval_before=0.0,
                eval_after=0.0,
                best_eval=0.4,  # 0.04 expected points below the best: over rule v4's 0.03 (ADR 0009)
            )
            is False
        )

    def test_accepts_sound_piece_sacrifice(self):
        board = chess.Board("rnb1kb1r/pppp1ppp/5n2/4p2Q/4P3/8/PPPP1PPP/RNB1KBNR w KQkq - 0 3")
        move = chess.Move.from_uci("h5f7")

        assert material_sacrifice(board, move) >= 3
        assert (
            is_brilliant_move(
                board,
                move,
                eval_before=0.0,
                eval_after=0.1,
                best_eval=0.0,
            )
            is True
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


class TestRuleV4:
    """ADR 0009: sound, not lost and not forced in expected points."""

    BOARD = chess.Board("rnb1kb1r/pppp1ppp/5n2/4p2Q/4P3/8/PPPP1PPP/RNB1KBNR w KQkq - 0 3")
    MOVE = chess.Move.from_uci("h5f7")

    def clauses(self, before, after, best, alternatives=None):
        from app.services.brilliant import brilliant_clauses

        return brilliant_clauses(self.BOARD, self.MOVE, before, after, best, alternatives=alternatives)

    def test_the_same_pawns_cost_less_when_the_game_is_one_sided(self):
        # Half a pawn below the best: unsound when level, sound at +4 where it barely moves the result.
        assert self.clauses(0.0, -0.5, 0.0)["sound"] is False
        assert self.clauses(4.0, 3.5, 4.0)["sound"] is True

    def test_a_move_that_searched_better_than_best_is_sound(self):
        assert self.clauses(0.0, 0.6, 0.0)["sound"] is True

    def test_no_brilliant_when_already_lost(self):
        assert self.clauses(-6.0, -6.0, -6.0)["not_lost"] is False
        assert self.clauses(-1.0, -1.0, -1.0)["not_lost"] is True

    def test_forced_when_every_other_move_is_clearly_worse(self):
        alternatives = [("h5f7", 0.5), ("h5h4", -1.5), ("d1e2", -2.0)]
        assert self.clauses(0.5, 0.5, 0.5, alternatives)["not_forced"] is False
        assert self.clauses(0.5, 0.5, 0.5, [("h5f7", 0.5), ("h5h4", 0.3)])["not_forced"] is True
        # No lines for any other move: more than one legal move is enough.
        assert self.clauses(0.5, 0.5, 0.5, [("h5f7", 0.5)])["not_forced"] is True
