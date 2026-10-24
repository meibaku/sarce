"""
Tal-style brilliant move detection.

A brilliant move is a sound sacrifice — material given up without a large eval drop.
See docs/PHASES.md for full criteria. Rule v4 (ADR 0009) judges soundness, lost positions and "forced" in expected
points: a quarter-pawn means a lot when level and nothing when the game is decided.
"""

from __future__ import annotations

import chess

from app.config import settings
from app.services.ep import cp_to_ep

PIECE_VALUES = {
    chess.PAWN: 1,
    chess.KNIGHT: 3,
    chess.BISHOP: 3,
    chess.ROOK: 5,
    chess.QUEEN: 9,
}

MIN_BRILLIANT_SACRIFICE_VALUE = PIECE_VALUES[chess.KNIGHT]
MAX_BRILLIANT_EVAL_LOSS = 0.25

# ADR 0004: a Brilliant move must also be hard to find — players at the relevant rating play it at
# most this often (human model probability of the played move).
FIND_RATE_MAX = 0.20

# Rule v4 (ADR 0009), in expected points from the mover's side.
SOUND_EP_LOSS = 0.03  # sound: at most this much EP below the best move
LOST_EP = 0.10  # no Brilliant when already lost: the same "decided" line chaos uses (lenses.config.DECIDED_LOW)
ALTERNATIVE_EP = 0.10  # not forced: another move kept you within this much EP of the best


def pawns_ep(pawns: float | None) -> float | None:
    """Expected points for an evaluation in pawns (mover's side)."""
    return None if pawns is None else cp_to_ep(pawns * 100)


def hard_to_find(probs: dict[str, float] | None, move_uci: str) -> bool | None:
    """True/False for the find-rate clause; None when there is no human-model data to judge by."""
    if not probs:
        return None
    return probs.get(move_uci, 0.0) <= FIND_RATE_MAX


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
    if board.is_en_passant(move):
        captured_value = PIECE_VALUES[chess.PAWN]

    before = material_for_side(board, color)
    board.push(move)
    after = material_for_side(board, color)
    immediate_loss = max(0, before - after)

    offered_loss = 0
    moved_piece_after = board.piece_at(move.to_square)
    if moved_piece_after and moved_piece_after.color == color:
        moved_value = piece_value(moved_piece_after)
        if any(reply.to_square == move.to_square for reply in board.legal_moves):
            offered_loss = max(offered_loss, moved_value - captured_value)

    board.pop()

    # Promotion changes the moved piece value; do not count that as a sacrifice.
    if moving_piece and move.promotion:
        offered_loss = min(offered_loss, piece_value(moving_piece) - captured_value)

    return max(immediate_loss, offered_loss)


def real_offer(board: chess.Board, move: chess.Move) -> int:
    """
    Material genuinely offered by `move`, or 0 (ADR 0007).

    Stricter than `material_sacrifice` (any piece a reply could land on): after the move the piece
    must be attacked by something cheaper, or attacked and undefended. A defended piece that can
    only be taken by an equal or bigger piece is not on offer.
    """
    piece = board.piece_at(move.from_square)
    if piece is None or move.promotion:
        return 0
    captured = board.piece_at(move.to_square)
    taken = PIECE_VALUES.get(captured.piece_type, 0) if captured else (1 if board.is_en_passant(move) else 0)
    after = board.copy(stack=False)
    after.push(move)
    attackers = after.attackers(not piece.color, move.to_square)
    if not attackers:
        return 0
    cheapest = min(PIECE_VALUES.get(after.piece_at(sq).piece_type, 100) for sq in attackers)
    defended = bool(after.attackers(piece.color, move.to_square))
    value = PIECE_VALUES.get(piece.piece_type, 0)
    if cheapest < value or not defended:
        return max(0, value - taken)
    return 0


def has_reasonable_alternatives(
    board: chess.Board, move: chess.Move, alternatives: list[tuple[str, float | None]] | None = None
) -> bool:
    """
    Not forced (ADR 0009): another move kept you within ALTERNATIVE_EP of the best, so the sacrifice was a choice.
    `alternatives` are the engine's lines before the move as (uci, eval in pawns). Without lines for any other
    move, more than one legal move is enough (nothing says the others lost).
    """
    legal = list(board.legal_moves)
    if len(legal) < 2 or move not in legal:
        return False
    scored = [(uci, pawns_ep(ev)) for uci, ev in alternatives or [] if ev is not None]
    others = [ep for uci, ep in scored if uci != move.uci()]
    if not others:
        return True
    best = max(ep for _, ep in scored)
    return any(best - ep <= ALTERNATIVE_EP for ep in others)


CLAUSES = ("real_sacrifice", "sound", "not_lost", "not_already_winning", "not_forced", "hard_to_find")
BOARD_CLAUSES = CLAUSES[:-1]  # judged at classification; the find-rate clause needs the human model (post-pass)


def first_failure(clauses: dict[str, bool | None]) -> str | None:
    """The first clause, in CLAUSES order, that is False; None when none fails."""
    return next((c for c in CLAUSES if clauses.get(c) is False), None)


def best_eval_from_row(m: dict) -> float | None:
    """
    The best move's evaluation for a stored `game_moves` row, as classification compared it: eval_after plus the
    centipawn loss. The loss is clamped at zero, but a clamped zero means the move scored at least as well as the
    best line, which passes the one-sided soundness test either way (and old engine-searched games stored a
    separate search of the best move that the PV doesn't hold).
    """
    if m.get("eval_after") is None:
        return None
    return m["eval_after"] + float(m.get("cp_loss") or 0) / 100


def alternatives_from_row(m: dict) -> list[tuple[str, float | None]]:
    """The engine lines before a stored move, as (uci, eval) for `has_reasonable_alternatives`."""
    return [(p["uci"], p.get("eval")) for p in m.get("pv") or [] if p.get("uci")]


def brilliant_clauses(
    board: chess.Board,
    move: chess.Move,
    eval_before: float | None,
    eval_after: float | None,
    best_eval: float | None,
    probs: dict[str, float] | None = None,
    alternatives: list[tuple[str, float | None]] | None = None,
) -> dict[str, bool | None]:
    """
    Each Brilliant clause on its own, in CLAUSES order: True/False, or None when it can't be judged (no evaluation,
    or no human-model data for the find-rate clause). `is_brilliant_move` is BOARD_CLAUSES; the find-rate clause
    (ADR 0004) is applied afterwards by the post-pass. Used to show which clause stops a move (review F6).
    Rule v4 (ADR 0009): sound, not_lost and not_forced are in expected points.
    """
    real = material_sacrifice(board, move) >= MIN_BRILLIANT_SACRIFICE_VALUE and real_offer(board, move) >= MIN_BRILLIANT_SACRIFICE_VALUE
    has_evals = eval_before is not None and eval_after is not None and best_eval is not None
    return {
        "real_sacrifice": real,  # ADR 0007: a minor piece or more genuinely on offer
        # One-sided: a move that searched better than the best line isn't unsound.
        "sound": pawns_ep(best_eval) - pawns_ep(eval_after) <= SOUND_EP_LOSS if has_evals else None,
        "not_lost": pawns_ep(eval_before) >= LOST_EP if has_evals else None,
        "not_already_winning": eval_before <= settings.brilliant_winning_margin if has_evals else None,
        "not_forced": has_reasonable_alternatives(board, move, alternatives),
        "hard_to_find": hard_to_find(probs, move.uci()),
    }


def is_brilliant_move(
    board: chess.Board,
    move: chess.Move,
    eval_before: float | None,
    eval_after: float | None,
    best_eval: float | None,
    alternatives: list[tuple[str, float | None]] | None = None,
) -> bool:
    """
    Tal-specific brilliant detection, rule v4. ALL conditions must hold (see `brilliant_clauses`):

    1. Real piece sacrifice (minor piece or larger, not a pawn), genuinely on offer (ADR 0007)
    2. Sound: at most SOUND_EP_LOSS expected points below the best move (ADR 0009)
    3. Not already lost: at least LOST_EP before the move (ADR 0009)
    4. Not already crushing (+3 pawns default, BRILLIANT_WINNING_MARGIN)
    5. Not forced: another move kept you within ALTERNATIVE_EP of the best (ADR 0009)

    The find-rate clause (ADR 0004) is applied afterwards by brilliant_find_rate.
    """
    if eval_before is None or eval_after is None or best_eval is None:
        return False
    clauses = brilliant_clauses(board, move, eval_before, eval_after, best_eval, alternatives=alternatives)
    return all(clauses[c] for c in BOARD_CLAUSES)


# "Almost Brilliant" (plan 3.3): a real sacrifice that missed exactly one clause, named in the player's words.
NEAR_PREFIX = "near_brilliant:"
NEAR_COPY = {
    "sound": "it gave a little more than the best move",
    "not_lost": "the game was already lost",
    "not_already_winning": "you were already winning",
    "not_forced": "every other move was clearly worse, so it was forced",
    "hard_to_find": f"players at your rating play it more often than the {round(FIND_RATE_MAX * 100)}% Brilliant cutoff",
}


def near_miss(clauses: dict[str, bool | None]) -> str | None:
    """The one clause a real sacrifice missed, or None (not a real sacrifice, Brilliant, or two or more missed)."""
    if not clauses.get("real_sacrifice"):
        return None
    missed = [c for c in CLAUSES[1:] if clauses.get(c) is False]
    return missed[0] if len(missed) == 1 else None


def definition() -> dict:
    """The rule in plain words with the thresholds the code uses (the public definition page)."""
    return {
        "rule": "v4",
        "clauses": [
            {"id": "real_sacrifice", "title": "A real sacrifice", "text": f"You offer at least {MIN_BRILLIANT_SACRIFICE_VALUE} points of material (a minor piece or more), counted after subtracting anything the move captures, and it is really on offer: attacked by something cheaper, or undefended. Pawns alone don't count."},
            {"id": "sound", "title": "It holds up", "text": f"The move costs at most {SOUND_EP_LOSS:.2f} expected points against the best move: no more than {round(SOUND_EP_LOSS * 100)} points off your winning chances."},
            {"id": "not_lost", "title": "The game is still open", "text": f"You still had at least {round(LOST_EP * 100)}% winning chances before the move."},
            {"id": "not_already_winning", "title": "Not already won", "text": f"You weren't already more than {settings.brilliant_winning_margin:g} pawns up."},
            {"id": "not_forced", "title": "A real choice", "text": f"Another move kept you within {ALTERNATIVE_EP:.2f} expected points of the best, so you chose the sacrifice."},
            {"id": "hard_to_find", "title": "Hard to find", "text": f"At most {round(FIND_RATE_MAX * 100)}% of players at your rating would play it, by the human model."},
        ],
        "thresholds": {
            "minSacrifice": MIN_BRILLIANT_SACRIFICE_VALUE,
            "soundEpLoss": SOUND_EP_LOSS,
            "lostEp": LOST_EP,
            "winningPawns": settings.brilliant_winning_margin,
            "alternativeEp": ALTERNATIVE_EP,
            "findRateMax": FIND_RATE_MAX,
        },
    }
