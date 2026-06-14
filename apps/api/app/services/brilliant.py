"""
Tal-style brilliant move detection.

A brilliant move is a sound sacrifice — material given up without a large eval drop.
See docs/PHASES.md for full criteria.
"""

from __future__ import annotations

import chess

from app.config import settings

PIECE_VALUES = {
    chess.PAWN: 1,
    chess.KNIGHT: 3,
    chess.BISHOP: 3,
    chess.ROOK: 5,
    chess.QUEEN: 9,
}


def piece_value(piece: chess.Piece | None) -> int:
    """Return simple material value for a piece."""
    if piece is None:
        return 0
    return PIECE_VALUES.get(piece.piece_type, 0)


def material_for_side(board: chess.Board, color: chess.Color) -> int:
    """Total material value for one side."""
    return sum(
        len(board.pieces(pt, color)) * val for pt, val in PIECE_VALUES.items()
    )


def material_sacrifice(board: chess.Board, move: chess.Move) -> int:
    """
    Positive value = material the moving side gives up or offers.

    Sacrifices are often offered before they are accepted, so this combines
    immediate material loss with the value of the moved piece if it can be
    captured on the opponent's next legal move.
    """
    color = board.turn
    moving_piece = board.piece_at(move.from_square)
    captured_piece = board.piece_at(move.to_square)
    captured_value = piece_value(captured_piece)

    before = material_for_side(board, color)
    board.push(move)
    after = material_for_side(board, color)
    immediate_loss = max(0, before - after)

    offered_loss = 0
    moved_piece_after = board.piece_at(move.to_square)
    if moved_piece_after and moved_piece_after.color == color:
        moved_value = piece_value(moved_piece_after)
        for reply in board.legal_moves:
            if reply.to_square == move.to_square:
                offered_loss = max(offered_loss, moved_value - captured_value)

    board.pop()

    # Promotion changes the moved piece value; do not count that as a sacrifice.
    if moving_piece and move.promotion:
        offered_loss = min(offered_loss, piece_value(moving_piece) - captured_value)

    return max(immediate_loss, offered_loss)


def has_reasonable_alternatives(board: chess.Board, move: chess.Move) -> bool:
    """Move is not forced — more than one legal option existed."""
    legal = list(board.legal_moves)
    return len(legal) > 1 and move in legal


def is_brilliant_move(
    board: chess.Board,
    move: chess.Move,
    eval_before: float | None,
    eval_after: float | None,
    best_eval: float | None,
) -> bool:
    """
    Tal-specific brilliant detection. ALL conditions must hold:

    1. Material sacrifice (piece value given up)
    2. Eval after move within margin of best available
    3. Position not already crushing (+3 pawns default)
    4. Not a forced-only move

    Thresholds: BRILLIANT_EVAL_MARGIN, BRILLIANT_WINNING_MARGIN in .env
    """
    if eval_before is None or eval_after is None or best_eval is None:
        return False

    if material_sacrifice(board, move) < 1:
        return False

    if abs(eval_after - best_eval) > settings.brilliant_eval_margin:
        return False

    if eval_before > settings.brilliant_winning_margin:
        return False

    if not has_reasonable_alternatives(board, move):
        return False

    return True
