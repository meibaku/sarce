"""Secondary move signals for style-oriented analysis.

These signals explain what a move meant without overloading the quality tier.
"""

from __future__ import annotations

from collections import Counter
from typing import TYPE_CHECKING, Any

import chess

from app.services.brilliant import material_sacrifice, piece_value

if TYPE_CHECKING:
    from app.services.move_classifier import MoveQuality

MoveSignal = str

OPENING_MAX_PLY = 16
ENDGAME_PIECE_THRESHOLD = 7
CLEARLY_BEST_MARGIN = 0.5
EVAL_SWING_THRESHOLD = 0.9
INITIATIVE_THRESHOLD = 0.45
MOMENTUM_SHIFT_THRESHOLD = 0.35


def game_phase(board: chess.Board, ply: int) -> str:
    """Return a coarse phase label for the current move."""
    if ply < OPENING_MAX_PLY:
        return "opening"

    non_pawn_pieces = 0
    for piece_type in (chess.QUEEN, chess.ROOK, chess.BISHOP, chess.KNIGHT):
        non_pawn_pieces += len(board.pieces(piece_type, chess.WHITE))
        non_pawn_pieces += len(board.pieces(piece_type, chess.BLACK))

    if non_pawn_pieces <= ENDGAME_PIECE_THRESHOLD:
        return "endgame"
    return "middlegame"


def move_san(board: chess.Board, move: chess.Move | None) -> str | None:
    if move is None or move not in board.legal_moves:
        return None
    return board.san(move)


def eval_swing(eval_before: float | None, eval_after: float | None) -> float | None:
    if eval_before is None or eval_after is None:
        return None
    return eval_after - eval_before


def is_clearly_best(
    best_eval: float | None,
    second_eval: float | None,
    played_is_best: bool,
) -> bool:
    if not played_is_best or best_eval is None or second_eval is None:
        return False
    return best_eval - second_eval >= CLEARLY_BEST_MARGIN


def is_exchange_sacrifice(
    board: chess.Board,
    move: chess.Move,
    sacrifice: int = 0,
) -> bool:
    moving_piece = board.piece_at(move.from_square)
    captured_piece = board.piece_at(move.to_square)
    if moving_piece is None or moving_piece.piece_type != chess.ROOK:
        return False
    captured_value = piece_value(captured_piece)
    return captured_value == 3 and sacrifice > 0


def is_tactical_move(board: chess.Board, move: chess.Move) -> bool:
    if board.is_capture(move):
        return True
    copy = board.copy()
    copy.push(move)
    return copy.is_check() or copy.is_checkmate()


def build_move_signals(
    *,
    board: chess.Board,
    move: chess.Move,
    quality: "MoveQuality | str",
    cp_loss: float,
    eval_before: float | None,
    eval_after: float | None,
    best_move: chess.Move | None,
    pv: list[dict[str, Any]],
    previous_user_eval_after: float | None,
) -> tuple[list[MoveSignal], str | None]:
    """Create secondary signals and one human-readable highlight."""
    signals: list[MoveSignal] = []
    highlight: str | None = None
    quality_value = getattr(quality, "value", quality)
    legal_count = board.legal_moves.count()
    sacrifice = material_sacrifice(board, move)
    swing = eval_swing(eval_before, eval_after)
    played_is_best = best_move == move
    second_eval = pv[1]["eval"] if len(pv) > 1 else None
    best_eval = pv[0]["eval"] if pv else None

    if legal_count <= 1:
        signals.append("forced")
        highlight = "Only legal move."

    if played_is_best:
        signals.append("top_engine_choice")
    elif any(candidate.get("move") == move for candidate in pv[:3]):
        signals.append("top_three_choice")

    if is_clearly_best(best_eval, second_eval, played_is_best):
        signals.append("clearly_best")

    if sacrifice > 0:
        signals.append("sacrifice")
    if is_exchange_sacrifice(board, move, sacrifice):
        signals.append("exchange_sacrifice")
        highlight = "Exchange sacrifice with compensation to inspect."

    if quality_value == "brilliant":
        signals.append("brilliant_sacrifice")
        highlight = "Sound sacrifice stayed close to the engine's best line."

    if swing is not None and abs(swing) >= EVAL_SWING_THRESHOLD:
        signals.append("evaluation_swing")
        if swing > 0:
            highlight = f"Evaluation improved by {swing:.1f} pawns."
        else:
            highlight = f"Evaluation dropped by {abs(swing):.1f} pawns."

    if (
        swing is not None
        and swing >= INITIATIVE_THRESHOLD
        and cp_loss <= 50
        and is_tactical_move(board, move)
    ):
        signals.append("tactical_resource")
        highlight = "Strong tactical resource with low engine loss."

    if (
        previous_user_eval_after is not None
        and eval_after is not None
        and previous_user_eval_after < -MOMENTUM_SHIFT_THRESHOLD
        and eval_after > MOMENTUM_SHIFT_THRESHOLD
    ):
        signals.append("momentum_shift")
        highlight = "Momentum shifted back in your favor."

    if sacrifice >= 3 and swing is not None and swing >= 0.2 and cp_loss <= 50:
        signals.append("breakthrough_sacrifice")
        highlight = "Sacrifice created a playable breakthrough."

    if quality_value == "miss":
        signals.append("missed_tactic")
        highlight = "A tactical chance slipped away."
    elif quality_value == "blunder":
        signals.append("critical_error")
        highlight = "Critical evaluation loss."

    if quality_value in {"best", "excellent"} and not signals:
        signals.append("clean_move")

    return list(dict.fromkeys(signals)), highlight


def signal_distribution(classified_moves: list[dict]) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for move in classified_moves:
        counts.update(move.get("signals", []))
    return dict(sorted(counts.items()))
