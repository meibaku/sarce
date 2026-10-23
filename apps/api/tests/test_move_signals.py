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

    def test_free_rook_capture_is_not_exchange_sacrifice(self):
        board = chess.Board("4k3/8/8/8/4b3/8/4R3/4K3 w - - 0 1")
        move = chess.Move.from_uci("e2e4")

        signals, _ = build_move_signals(
            board=board,
            move=move,
            quality=MoveQuality.BEST,
            cp_loss=0,
            eval_before=0.0,
            eval_after=1.0,
            best_move=move,
            pv=[{"move": move, "eval": 1.0}],
            previous_user_eval_after=None,
        )

        assert "exchange_sacrifice" not in signals

    def test_rook_capture_minor_under_attack_is_exchange_sacrifice(self):
        board = chess.Board("4k3/8/5n2/8/4b3/8/4R3/4K3 w - - 0 1")
        move = chess.Move.from_uci("e2e4")

        signals, _ = build_move_signals(
            board=board,
            move=move,
            quality=MoveQuality.BEST,
            cp_loss=0,
            eval_before=0.0,
            eval_after=0.2,
            best_move=move,
            pv=[{"move": move, "eval": 0.2}],
            previous_user_eval_after=None,
        )

        assert "exchange_sacrifice" in signals


def signals_for(sans: list[str], uci: str) -> list[str]:
    board = chess.Board()
    for san in sans:
        board.push_san(san)
    move = chess.Move.from_uci(uci)
    signals, _ = build_move_signals(
        board=board, move=move, quality=MoveQuality.GOOD, cp_loss=0, eval_before=0.0, eval_after=0.0,
        best_move=move, pv=[{"move": move, "eval": 0.0}], previous_user_eval_after=None,
    )
    return signals


class TestRealSacrifice:
    """review F2: the Sacrifice trait reads real_sacrifice (a piece genuinely on offer), not the loose tag."""

    def test_a_knight_left_to_a_pawn_is_a_real_sacrifice(self):
        # 1.e4 c6 2.Nc3 e6 3.Nb5: the c6 pawn takes the knight.
        s = signals_for(["e4", "c6", "Nc3", "e6"], "c3b5")
        assert "sacrifice" in s and "real_sacrifice" in s

    def test_a_defended_knight_only_a_knight_attacks_is_not(self):
        # 1.e4 e5 2.Nf3 Nc6 3.d4 Nf6 4.Nxe5: only the c6 knight attacks it and d4 defends it.
        s = signals_for(["e4", "e5", "Nf3", "Nc6", "d4", "Nf6"], "f3e5")
        assert "sacrifice" in s and "real_sacrifice" not in s
