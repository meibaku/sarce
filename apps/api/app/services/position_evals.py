"""
Position evaluation cache — raw engine data for the Chaos Lens (docs/CHAOS_PLAN.md, M1).

Engines write here; lenses only read (rule 3). Every search is node-limited and looked up
by position first, so re-analysing a game is deterministic and adding a lens never needs
a new engine run.
"""

from __future__ import annotations

import logging
from typing import Protocol

import chess

from app.config import settings
from app.db.supabase import get_supabase
from app.services.ep import cp_to_ep, is_decided
from app.services.move_classifier import is_user_ply

logger = logging.getLogger(__name__)

TABLE = "position_evals"


def fen_key(board: chess.Board) -> str:
    """
    Cache identity for a position: the FEN without the fullmove number.

    The halfmove clock is kept — it changes fifty-move-rule evaluations.
    """
    return board.fen().rsplit(" ", 1)[0]


class LineEngine(Protocol):
    """The slice of StockfishEngine this module needs; lets tests pass a fake."""

    engine_version: str

    def analyse(self, board: chess.Board, nodes: int, multipv: int) -> list[dict]: ...


class EvalStore(Protocol):
    def get(self, key: str, nodes: int) -> dict | None: ...

    def put(self, row: dict) -> None: ...


class SupabaseEvalStore:
    """`position_evals` rows keyed by (fen_key, nodes)."""

    def get(self, key: str, nodes: int) -> dict | None:
        res = (
            get_supabase()
            .table(TABLE)
            .select("*")
            .eq("fen_key", key)
            .eq("nodes", nodes)
            .limit(1)
            .execute()
        )
        return res.data[0] if res.data else None

    def put(self, row: dict) -> None:
        get_supabase().table(TABLE).upsert(row, on_conflict="fen_key,nodes").execute()


def safe_set_complete(lines: list[dict], tol: float) -> bool:
    """
    True when the stored lines provably contain every reply within `tol` EP of the best.

    Lines are ordered best first, so the set is complete once the last line falls outside
    the tolerance. No lines, or a missing EP, cannot prove anything and count as incomplete.
    """
    if not lines:
        return False
    best, last = lines[0].get("ep"), lines[-1].get("ep")
    if best is None or last is None:
        return False
    return best - last > tol


def evaluate_position(
    board: chess.Board,
    engine: LineEngine,
    store: EvalStore,
    *,
    nodes: int | None = None,
    multipv: int | None = None,
    multipv_cap: int | None = None,
    safe_tol: float | None = None,
) -> dict | None:
    """
    Return the stored evaluation row for `board`, searching only when the cache cannot answer.

    MultiPV widens (doubling, up to `multipv_cap`) while the last line is still inside the
    safe tolerance, so the safe set of replies is complete whenever the cap allows. A cached
    row is reused only if it still satisfies the current settings; otherwise it is widened
    and replaced. Returns None for positions with no legal moves or when the engine gave
    no usable line (nothing is cached in that case).
    """
    nodes = nodes or settings.analysis_nodes
    multipv = multipv or settings.analysis_multipv
    multipv_cap = multipv_cap or settings.analysis_multipv_cap
    safe_tol = settings.safe_set_tol if safe_tol is None else safe_tol

    legal_count = board.legal_moves.count()
    if legal_count == 0:
        return None

    key = fen_key(board)
    cap = min(max(multipv, multipv_cap), legal_count)
    target = min(multipv, cap)

    cached = store.get(key, nodes)
    lines = cached["lines"] if cached else []
    width = cached["multipv"] if cached else 0
    searched = False
    if width < target:
        width = target
        lines = engine.analyse(board, nodes=nodes, multipv=width)
        searched = True
    while width < cap and not safe_set_complete(lines, safe_tol):
        width = min(width * 2, cap)
        lines = engine.analyse(board, nodes=nodes, multipv=width)
        searched = True

    if not searched:
        return cached
    if not lines:
        logger.warning("Engine returned no usable line for %s; not cached", key)
        return None

    row = {
        "fen_key": key,
        "nodes": nodes,
        "multipv": width,
        "lines": lines,
        # False when the cap stopped the widening first; lenses must treat the set as partial.
        "safe_set_complete": width >= legal_count or safe_set_complete(lines, safe_tol),
        "engine_version": engine.engine_version,
    }
    store.put(row)
    return row


def mover_ep_before(ply: int, user_color: str, phase1_by_ply: dict[int, dict]) -> float | None:
    """
    The mover's EP before `ply`, converted from stored Phase 1 evals (pawns).

    User plies carry `eval_before`; an opponent ply mirrors the user's `eval_after` from
    the ply before it. None when Phase 1 has no eval for that moment.
    """
    if is_user_ply(ply, user_color):
        pawns = (phase1_by_ply.get(ply) or {}).get("eval_before")
        return None if pawns is None else cp_to_ep(pawns * 100)
    pawns = (phase1_by_ply.get(ply - 1) or {}).get("eval_after")
    return None if pawns is None else cp_to_ep(-pawns * 100)


def evaluate_game_positions(
    board: chess.Board,
    moves: list[chess.Move],
    user_color: str,
    classified: list[dict],
    engine: LineEngine,
    store: EvalStore,
) -> dict[str, int]:
    """
    Store an evaluation for the position after every ply, both players.

    The chaos lens reads positions after user moves; the survival lens needs the ones
    after opponent moves. Plies made from an already decided position are skipped.
    """
    phase1_by_ply = {m["ply"]: m for m in classified}
    stats = {"evaluated": 0, "skipped_decided": 0, "terminal": 0, "failed": 0}
    temp = board.copy()
    for ply, move in enumerate(moves):
        before = mover_ep_before(ply, user_color, phase1_by_ply)
        temp.push(move)
        if is_decided(before, settings.ep_decided_low, settings.ep_decided_high):
            stats["skipped_decided"] += 1
            continue
        if temp.legal_moves.count() == 0:
            stats["terminal"] += 1
            continue
        row = evaluate_position(temp, engine, store)
        stats["failed" if row is None else "evaluated"] += 1
    return stats
