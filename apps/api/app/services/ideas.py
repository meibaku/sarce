"""
Idea windows — Chaos Lens M7 (docs/CHAOS_PLAN.md): "did I have an idea, did it land, did I pivot?"

Rule-based and engine-free. An idea is a stretch of the user's play that fits one of a
few families (gambit, king attack, squeeze); its verdict comes from how the user's
expected points moved afterwards. Thresholds are configurable starting points, not
calibrated truths, and the labels describe what happened — they do not grade the player.
"""

from __future__ import annotations

from dataclasses import dataclass

import chess

from app.services.brilliant import material_for_side
from app.services.ep import cp_to_ep

GAMBIT_MIN_DEFICIT = 1  # pawns
GAMBIT_MIN_PLIES = 6
GAMBIT_MIN_EP = 0.40

KING_ATTACK_MIN_UNITS = 3
KING_ATTACK_WINDOW = 8  # plies

SQUEEZE_WINDOW = 10  # plies
SQUEEZE_MOBILITY_DROP = 0.30  # share of the opponent's legal moves lost
SQUEEZE_EP_GAIN = 0.10

VERDICT_LOOKAHEAD = 4  # plies after the window closes
WORKED_EP_GAIN = 0.10
WORKED_EP_LEVEL = 0.70
REFUTED_EP_LOSS = 0.15
PIVOT_WINDOW = 12  # plies after a refuted idea


@dataclass(frozen=True)
class PlyState:
    """What the idea rules need to know about the position after one ply."""

    ply: int
    by_user: bool
    material_diff: int  # user's material minus the opponent's, in pawns
    opponent_mobility: int | None  # opponent's legal moves, known after a user move
    entered_king_zone: bool  # a user piece moved into the enemy king zone on this ply
    user_ep: float | None  # user's expected points, known after a user move


def king_zone(board: chess.Board, color: chess.Color) -> chess.SquareSet:
    """Squares within one step of `color`'s king, plus the three squares in front of that ring."""
    king = board.king(color)
    if king is None:
        return chess.SquareSet()
    zone = chess.SquareSet(chess.BB_KING_ATTACKS[king]) | chess.SquareSet([king])
    forward = 2 if color == chess.WHITE else -2
    rank = chess.square_rank(king) + forward
    if 0 <= rank <= 7:
        for file in range(max(0, chess.square_file(king) - 1), min(7, chess.square_file(king) + 1) + 1):
            zone.add(chess.square(file, rank))
    return zone


def build_ply_states(
    board: chess.Board,
    moves: list[chess.Move],
    user_color: str,
    eval_after_by_ply: dict[int, float | None],
) -> list[PlyState]:
    """Replay the game and collect the per-ply facts. `eval_after_by_ply` is Phase 1 data (pawns)."""
    user = chess.WHITE if user_color == "white" else chess.BLACK
    temp, states = board.copy(), []
    for ply, move in enumerate(moves):
        by_user = temp.turn == user
        piece = temp.piece_at(move.from_square)
        entered = (
            by_user
            and piece is not None
            and piece.piece_type not in (chess.PAWN, chess.KING)
            and move.to_square in king_zone(temp, not user)
            and move.from_square not in king_zone(temp, not user)
        )
        temp.push(move)
        pawns = eval_after_by_ply.get(ply) if by_user else None
        states.append(
            PlyState(
                ply=ply,
                by_user=by_user,
                material_diff=material_for_side(temp, user) - material_for_side(temp, not user),
                opponent_mobility=temp.legal_moves.count() if by_user else None,
                entered_king_zone=entered,
                user_ep=None if pawns is None else cp_to_ep(float(pawns) * 100),
            )
        )
    return states


def _ep_near(states: list[PlyState], ply: int, forward: bool) -> float | None:
    """The user's EP at `ply`, or the nearest known value after (or before) it."""
    order = range(ply, len(states)) if forward else range(min(ply, len(states) - 1), -1, -1)
    for index in order:
        if states[index].user_ep is not None:
            return states[index].user_ep
    return None


def verdict_for(states: list[PlyState], start: int, end: int) -> str:
    """worked / refuted / fizzled from the user's EP before the idea and shortly after it."""
    before = _ep_near(states, start, forward=False)
    after_ply = min(len(states) - 1, end + VERDICT_LOOKAHEAD)
    after = _ep_near(states, after_ply, forward=False)
    if before is None or after is None:
        return "fizzled"
    if after - before >= WORKED_EP_GAIN or (after >= WORKED_EP_LEVEL and after >= before):
        return "worked"
    if before - after >= REFUTED_EP_LOSS:
        return "refuted"
    return "fizzled"


def find_gambits(states: list[PlyState]) -> list[tuple[int, int]]:
    """Stretches where the user stays a pawn or more down while keeping a playable position."""
    windows, start = [], None
    for state in states:
        down = state.material_diff <= -GAMBIT_MIN_DEFICIT
        playable = state.user_ep is None or state.user_ep >= GAMBIT_MIN_EP
        if down and playable:
            start = state.ply if start is None else start
            continue
        if start is not None and state.ply - start >= GAMBIT_MIN_PLIES:
            windows.append((start, state.ply - 1))
        start = None
    if start is not None and len(states) - start >= GAMBIT_MIN_PLIES:
        windows.append((start, len(states) - 1))
    return windows


def find_king_attacks(states: list[PlyState]) -> list[tuple[int, int]]:
    """Windows where several user pieces arrive in the enemy king zone in quick succession."""
    entries = [s.ply for s in states if s.entered_king_zone]
    windows, index = [], 0
    while index + KING_ATTACK_MIN_UNITS <= len(entries):
        first = entries[index]
        inside = [p for p in entries[index:] if p - first < KING_ATTACK_WINDOW]
        if len(inside) >= KING_ATTACK_MIN_UNITS:
            windows.append((first, inside[-1]))
            index += len(inside)
        else:
            index += 1
    return windows


def find_squeezes(states: list[PlyState]) -> list[tuple[int, int]]:
    """Windows where the opponent's options shrink while the user's expected points rise."""
    user_states = [s for s in states if s.by_user and s.opponent_mobility and s.user_ep is not None]
    windows, last_end = [], -1
    for i, first in enumerate(user_states):
        if first.ply <= last_end:
            continue
        for later in user_states[i + 1 :]:
            if later.ply - first.ply > SQUEEZE_WINDOW:
                break
            dropped = 1 - later.opponent_mobility / first.opponent_mobility
            if dropped >= SQUEEZE_MOBILITY_DROP and later.user_ep - first.user_ep >= SQUEEZE_EP_GAIN:
                windows.append((first.ply, later.ply))
                last_end = later.ply
                break
    return windows


def find_ideas(states: list[PlyState]) -> list[dict]:
    """All idea windows in ply order, each with a verdict; pivots are marked after refutations."""
    found = (
        [("gambit", window) for window in find_gambits(states)]
        + [("king_attack", window) for window in find_king_attacks(states)]
        + [("squeeze", window) for window in find_squeezes(states)]
    )
    ideas = [
        {
            "family": family,
            "start_ply": start,
            "end_ply": end,
            "verdict": verdict_for(states, start, end),
            "is_pivot": False,
        }
        for family, (start, end) in sorted(found, key=lambda item: (item[1][0], item[0]))
    ]
    for index, idea in enumerate(ideas):
        if idea["verdict"] != "refuted":
            continue
        for later in ideas[index + 1 :]:
            if later["start_ply"] > idea["end_ply"] + PIVOT_WINDOW:
                break
            if later["start_ply"] > idea["end_ply"] and later["family"] != idea["family"]:
                later["is_pivot"] = True
                break
    return ideas
