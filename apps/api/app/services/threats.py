"""
Threat raw data for the prophylaxis lens: in each position the user faced, what would the opponent play if it were
their move again (a null-move search)? Stored per position like `position_evals`, so the lens stays a pure read.

The threat's size is how much better the opponent's best move in that "passed" position is than their standing
after the user's best reply: a big number means there was an idea to stop.
"""

from __future__ import annotations

import logging

import chess

from app.db.supabase import get_supabase
from app.lenses.squeeze import line_cp
from app.services.position_evals import fen_key, iter_live_positions

logger = logging.getLogger(__name__)

TABLE = "position_threats"
THREAT_NODES = 150_000  # a short search: the threat only needs to be found, not evaluated to the last pawn


def null_move_threat(board: chess.Board, engine, nodes: int = THREAT_NODES) -> dict | None:
    """The opponent's best move and score (their side) if the side to move passed; None in check or at the end."""
    if board.is_check() or board.is_game_over():
        return None
    # Hand the move to the other side without a null move in the history (the UCI engine can't be sent one).
    passed = board.copy(stack=False)
    passed.turn = not passed.turn
    passed.ep_square = None
    if not passed.is_valid() or passed.is_game_over() or not any(passed.legal_moves):
        return None
    lines = engine.analyse(passed, nodes=nodes, multipv=1)
    if not lines:
        return None
    cp = line_cp(lines[0])
    return None if cp is None else {"threat_uci": lines[0]["move_uci"], "threat_cp": cp}


class SupabaseThreatStore:
    def get(self, key: str, nodes: int) -> dict | None:
        res = get_supabase().table(TABLE).select("*").eq("fen_key", key).eq("nodes", nodes).limit(1).execute()
        return res.data[0] if res.data else None

    def put(self, row: dict) -> None:
        get_supabase().table(TABLE).upsert(row, on_conflict="fen_key,nodes").execute()


def evaluate_game_threats(board: chess.Board, moves: list[chess.Move], user_color: str, classified: list[dict], engine, store) -> dict[str, int]:
    """Store a threat for every live position the user had to move in (after an opponent move); cached by key."""
    you = chess.WHITE if user_color == "white" else chess.BLACK
    stats = {"stored": 0, "cached": 0, "none": 0}
    for _ply, position in iter_live_positions(board, moves, user_color, classified):
        if position.turn != you:
            continue
        key = fen_key(position)
        if store.get(key, THREAT_NODES):
            stats["cached"] += 1
            continue
        threat = null_move_threat(position, engine)
        if threat is None:
            stats["none"] += 1
            continue
        store.put({"fen_key": key, "nodes": THREAT_NODES, **threat})
        stats["stored"] += 1
    return stats
