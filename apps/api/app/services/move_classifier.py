"""
Move quality classification — Chess.com-style tiers from Stockfish output.

Rule-based (no ML). See docs/PHASES.md for tier definitions.
"""

from __future__ import annotations

from enum import Enum

import chess

from app.services.brilliant import is_brilliant_move
from app.services.move_signals import (
    build_move_signals,
    game_phase,
    move_san,
)
from app.services.stockfish import StockfishEngine


class MoveQuality(str, Enum):
    BEST = "best"
    EXCELLENT = "excellent"
    GOOD = "good"
    INACCURACY = "inaccuracy"
    MISTAKE = "mistake"
    BLUNDER = "blunder"
    MISS = "miss"
    BRILLIANT = "brilliant"


# Centipawn loss thresholds (Chess.com-style approximations)
THRESHOLDS = [
    (0, MoveQuality.BEST),
    (25, MoveQuality.EXCELLENT),
    (50, MoveQuality.GOOD),
    (100, MoveQuality.INACCURACY),
    (200, MoveQuality.MISTAKE),
    (400, MoveQuality.BLUNDER),
]

# Miss: had winning advantage, lost the opportunity
MISS_WINNING_THRESHOLD = 1.5  # pawns
MISS_AFTER_THRESHOLD = 0.8


def centipawn_loss_to_quality(cp_loss: float) -> MoveQuality:
    """Map centipawn loss to a quality tier."""
    for threshold, quality in THRESHOLDS:
        if cp_loss <= threshold:
            return quality
    return MoveQuality.BLUNDER


def is_miss(
    eval_before: float | None,
    eval_after: float | None,
    cp_loss: float,
) -> bool:
    """
    Detect missed win — had significant advantage, played move that loses it.

    Phase 1 heuristic; tune against real game samples in Phase 3.
    """
    if eval_before is None or eval_after is None:
        return False
    return (
        eval_before >= MISS_WINNING_THRESHOLD
        and eval_after < MISS_AFTER_THRESHOLD
        and cp_loss >= 100
    )


def is_user_ply(ply: int, user_color: str) -> bool:
    """Return True if this ply is the user's move (white: even, black: odd)."""
    if user_color == "white":
        return ply % 2 == 0
    return ply % 2 == 1


def classify_move_quality(
    cp_loss: float,
    eval_before: float | None,
    eval_after: float | None,
) -> MoveQuality:
    """Assign quality tier including miss detection."""
    if is_miss(eval_before, eval_after, cp_loss):
        return MoveQuality.MISS
    return centipawn_loss_to_quality(cp_loss)


class MoveClassifier:
    """
    Classify all user moves in a game using a shared Stockfish session.

    Only moves by `user_color` are classified; opponent moves are skipped
    but the board state advances for both.
    """

    def classify_game(
        self,
        board: chess.Board,
        moves: list[chess.Move],
        user_color: str,
    ) -> list[dict]:
        """
        Classify user moves. Returns list of dicts with ply, uci, quality, evals.

        Args:
            board: Starting position from PGN headers.
            moves: Mainline moves.
            user_color: 'white' or 'black'.
        """
        results: list[dict] = []

        with StockfishEngine() as engine:
            temp = board.copy()
            previous_user_eval_after: float | None = None
            for ply, move in enumerate(moves):
                if not is_user_ply(ply, user_color):
                    temp.push(move)
                    continue

                phase = game_phase(temp, ply)
                san = temp.san(move)
                pv_candidates = engine.analyze_position_multipv(temp, multipv=3)
                best_before = pv_candidates[0]["move"] if pv_candidates else None
                eval_before = pv_candidates[0]["eval"] if pv_candidates else None
                eval_after, _ = engine.eval_after_move(temp, move)
                best_eval_after = eval_before
                if best_before:
                    best_eval_after, _ = engine.eval_after_move(temp, best_before)

                cp_loss = 0.0
                if best_eval_after is not None and eval_after is not None:
                    cp_loss = max(0.0, (best_eval_after - eval_after) * 100)

                quality = classify_move_quality(cp_loss, eval_before, eval_after)
                brilliant = False

                if best_before:
                    brilliant = is_brilliant_move(
                        board=temp,
                        move=move,
                        eval_before=eval_before,
                        eval_after=eval_after,
                        best_eval=best_eval_after,
                    )
                    if brilliant:
                        quality = MoveQuality.BRILLIANT

                pv = [
                    {
                        "rank": index + 1,
                        "uci": candidate["move"].uci() if candidate.get("move") else None,
                        "san": move_san(temp, candidate.get("move")),
                        "eval": candidate.get("eval"),
                    }
                    for index, candidate in enumerate(pv_candidates)
                ]
                signals, highlight = build_move_signals(
                    board=temp,
                    move=move,
                    quality=quality,
                    cp_loss=cp_loss,
                    eval_before=eval_before,
                    eval_after=eval_after,
                    best_move=best_before,
                    pv=pv_candidates,
                    previous_user_eval_after=previous_user_eval_after,
                )

                results.append(
                    {
                        "ply": ply,
                        "uci": move.uci(),
                        "san": san,
                        "quality": quality.value,
                        "cp_loss": round(cp_loss, 1),
                        "eval_before": eval_before,
                        "eval_after": eval_after,
                        "is_brilliant": brilliant,
                        "phase": phase,
                        "signals": signals,
                        "highlight": highlight,
                        "best_uci": best_before.uci() if best_before else None,
                        "best_san": move_san(temp, best_before),
                        "pv": pv,
                    }
                )
                previous_user_eval_after = eval_after
                temp.push(move)

        return results
