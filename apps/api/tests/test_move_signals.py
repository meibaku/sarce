import chess

from app.services.move_classifier import MoveQuality
from app.services.move_signals import build_move_signals, game_phase


class TestGamePhase:
    def test_opening_by_early_ply(self):
        assert game_phase(chess.Board(), 4) == "opening"

    def test_endgame_by_remaining_pieces(self):
        board = chess.Board("8/8/8/8/8/8/4K3/4k3 w - - 0 1")
        assert game_phase(board, 40) == "endgame"


class TestMoveSignals:
    def test_brilliant_move_gets_sound_sacrifice_signal(self):
        board = chess.Board()
        move = chess.Move.from_uci("g1f3")

        signals, highlight = build_move_signals(
            board=board,
            move=move,
            quality=MoveQuality.BRILLIANT,
            cp_loss=0,
            eval_before=0.0,
            eval_after=0.1,
            best_move=move,
            pv=[{"move": move, "eval": 0.1}],
            previous_user_eval_after=None,
        )

        assert "brilliant_sacrifice" in signals
        assert highlight == "Sound sacrifice stayed close to the engine's best line."

    def test_clear_best_uses_second_pv_gap(self):
        board = chess.Board()
        move = chess.Move.from_uci("g1f3")

        signals, _ = build_move_signals(
            board=board,
            move=move,
            quality=MoveQuality.BEST,
            cp_loss=0,
            eval_before=0.0,
            eval_after=0.2,
            best_move=move,
            pv=[
                {"move": move, "eval": 0.3},
                {"move": chess.Move.from_uci("b1c3"), "eval": -0.3},
            ],
            previous_user_eval_after=None,
        )

        assert "top_engine_choice" in signals
        assert "clearly_best" in signals

    def test_miss_gets_missed_tactic_signal(self):
        board = chess.Board()
        move = chess.Move.from_uci("g1f3")

        signals, highlight = build_move_signals(
            board=board,
            move=move,
            quality=MoveQuality.MISS,
            cp_loss=150,
            eval_before=2.0,
            eval_after=0.5,
            best_move=chess.Move.from_uci("e2e4"),
            pv=[],
            previous_user_eval_after=None,
        )

        assert "missed_tactic" in signals
        assert highlight == "A tactical chance slipped away."
