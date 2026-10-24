"""
"Chess.com called this Brilliant" (implementation plan 3.3, part 2).

When the player says another site marked a move Brilliant that Sarce didn't, the clause Sarce's rule stopped at
is worked out from stored data (the same clauses as the verdict, the find-rate probability from the cache only)
and stored with the report. Never "Sarce was wrong": it's calibration data for Benchmark B (plan 4.2), and the
player is told which clause made the difference.
"""

from __future__ import annotations

from datetime import datetime, timezone

from app.db.supabase import get_supabase
from app.services.brilliant import (
    alternatives_from_row,
    best_eval_from_row,
    brilliant_clauses,
    definition,
    first_failure,
    hard_to_find,
)
from app.services.brilliant_find_rate import RULE, mover_rung
from app.services.library import boards_before
from app.services.position_evals import fen_key

SOURCES = ("chess_com", "lichess")


def clause_title(clause: str) -> str:
    return next((c["title"] for c in definition()["clauses"] if c["id"] == clause), "one of the conditions")


class BrilliantReportService:
    def failed_clause(self, game: dict, row: dict) -> str:
        """The first clause Sarce's rule stopped at for this stored move, or "unknown" without the data to judge."""
        plies = boards_before(game.get("pgn") or "")
        if row["ply"] >= len(plies):
            return "unknown"
        board, move = plies[row["ply"]]
        clauses = brilliant_clauses(
            board, move, row.get("eval_before"), row.get("eval_after"), best_eval_from_row(row), alternatives=alternatives_from_row(row)
        )
        probs = (
            get_supabase().table("human_probs").select("probs").eq("fen_key", fen_key(board)).eq("elo", mover_rung(game))
            .limit(1).execute().data
            or []
        )
        clauses["hard_to_find"] = hard_to_find(probs[0]["probs"] if probs else None, row["uci"])
        return first_failure(clauses) or "unknown"

    def report(self, game_id: str, ply: int, source: str, user_id: str | None) -> dict | None:
        """Stores the report (one per move and site) and says which clause made the difference; None if no such move."""
        if source not in SOURCES:
            raise ValueError(f"source must be one of {SOURCES}")
        sb = get_supabase()
        games = sb.table("games").select("pgn, opponent_rating, user_rating, source, time_control").eq("id", game_id).limit(1).execute().data or []
        rows = (
            sb.table("game_moves").select("ply, uci, eval_before, eval_after, cp_loss, best_uci, pv, is_brilliant")
            .eq("game_id", game_id).eq("ply", ply).limit(1).execute().data
            or []
        )
        if not games or not rows:
            return None
        clause = self.failed_clause(games[0], rows[0])
        sb.table("brilliant_reports").upsert(
            {
                "game_id": game_id, "ply": ply, "user_id": user_id, "source": source, "failed_clause": clause,
                "rule": RULE, "created_at": datetime.now(timezone.utc).isoformat(),
            },
            on_conflict="game_id,ply,source",
        ).execute()
        site = "Chess.com" if source == "chess_com" else "Lichess"
        line = (
            f"Thanks. Sarce's rule stopped at “{clause_title(clause)}”; {site}'s Brilliant is a different definition. "
            "Your report helps check where the two differ."
            if clause != "unknown"
            else f"Thanks. There wasn't enough stored data to say which condition differed from {site}; the report is kept."
        )
        return {"clause": clause, "line": line}


def summary() -> dict[str, int]:
    """Reports by the clause Sarce stopped at (for Benchmark B): where the definitions part ways most."""
    rows = get_supabase().table("brilliant_reports").select("failed_clause").limit(10_000).execute().data or []
    out: dict[str, int] = {}
    for r in rows:
        out[r["failed_clause"]] = out.get(r["failed_clause"], 0) + 1
    return dict(sorted(out.items(), key=lambda kv: -kv[1]))

