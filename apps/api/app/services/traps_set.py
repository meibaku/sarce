"""
Your traps: the opening positions you steer into where opponents most often go wrong on the very next move.

The trap atlas (traps.py) is the defensive side: traps at your rating band to avoid. This is the other side, from
your own finished games. For every move you play in the first MAX_PLY plies, the opponent's actual reply is
compared with the stored engine lines for that position (`position_evals`, no new engine work): a reply that
drops TRAP_CP or more below their best is a trap that caught them. Positions reached at least MIN_SEEN times are
grouped and ranked by a cautious estimate of how often they catch opponents: the Wilson lower bound of caught/seen
(review F7), so a 3-of-3 fluke doesn't outrank 20 of 40. Rebuilt on request and stored (`traps_set`).
"""

from __future__ import annotations

import io
import logging
from collections import Counter
from datetime import datetime, timezone

import chess
import chess.pgn

from app.config import settings
from app.db.supabase import get_supabase
from app.lenses.squeeze import line_cp
from app.services.position_evals import fen_key
from app.services.uncertainty import wilson

logger = logging.getLogger(__name__)

MAX_PLY = 24  # the opening stretch
MIN_SEEN = 3  # a trap position must come up at least this often
MIN_CAUGHT = 2
TRAP_CP = 150  # a reply this much below the opponent's best counts as falling for it
TOP = 10
GAMES_READ = 800
CHUNK = 40  # fen keys per `in` filter


def reached_positions(games: list[dict]) -> dict[str, dict]:
    """Positions after your moves (opponent to move): {key: {fen, line, move, seen, replies: Counter}}."""
    out: dict[str, dict] = {}
    for g in games:
        game = chess.pgn.read_game(io.StringIO(g.get("pgn") or ""))
        if game is None:
            continue
        you = chess.WHITE if g.get("user_color") == "white" else chess.BLACK
        moves = list(game.mainline_moves())[: MAX_PLY + 1]
        board, sans = game.board(), []
        for ply, move in enumerate(moves[:MAX_PLY]):
            mover = board.turn
            san = board.san(move)
            sans.append(san)
            board.push(move)
            if mover != you or ply + 1 >= len(moves):
                continue
            key = fen_key(board)
            entry = out.setdefault(key, {"fen": board.fen(), "line": " ".join(sans), "move": san, "seen": 0, "replies": Counter()})
            entry["seen"] += 1
            entry["replies"][moves[ply + 1].uci()] += 1
    return {k: v for k, v in out.items() if v["seen"] >= MIN_SEEN}


def score_trap(entry: dict, lines: list[dict]) -> dict | None:
    """How often the opponent fell for it here: replies at least TRAP_CP below their best."""
    scored = [(ln["move_uci"], line_cp(ln)) for ln in lines if line_cp(ln) is not None]
    if not scored:
        return None
    best_uci, best = scored[0]
    by_move = dict(scored)
    worst = scored[-1][1]
    caught, gains, slips = 0, [], Counter()
    for uci, n in entry["replies"].items():
        cp = by_move.get(uci)
        if cp is None:
            # Not among the stored lines: at best as good as the weakest stored line, often far worse.
            if best - worst < TRAP_CP:
                continue
            cp = worst
        if best - cp >= TRAP_CP:
            caught += n
            gains += [best - cp] * n
            slips[uci] += n
    if caught < MIN_CAUGHT:
        return None
    board = chess.Board(entry["fen"])
    slip_uci = slips.most_common(1)[0][0]
    return {
        "caught": caught,
        "rate": round(caught / entry["seen"], 3),
        "gain_cp": round(sum(gains) / len(gains)),
        "slip": board.san(chess.Move.from_uci(slip_uci)),
        "defence": board.san(chess.Move.from_uci(best_uci)),
    }


def likely_rate(caught: int, seen: int) -> float:
    """The rate we can stand behind: the Wilson 95% lower bound of caught/seen (review F7, the winner's curse)."""
    interval = wilson(caught, seen)
    return round(interval[0], 3) if interval else 0.0


def to_api(row: dict) -> dict:
    return {
        "fen": row["fen"],
        "line": row["line"],
        "move": row["user_move"],
        "seen": row["seen"],
        "caught": row["caught"],
        "rate": row["rate"],
        "likely": likely_rate(row["caught"], row["seen"]),
        "gainPawns": round(row["gain_cp"] / 100, 1),
        "slip": row["slip"],
        "defence": row["defence"],
    }


class TrapsSetService:
    def build(self, owner_id: str) -> dict:
        """Recomputes the owner's traps from stored evaluations (no engine) and replaces the stored set."""
        sb = get_supabase()
        games = (
            sb.table("games").select("pgn, user_color").eq("user_id", owner_id).eq("analysis_status", "complete").neq("source", "sarce_bot")
            .order("played_at", desc=True).limit(GAMES_READ).execute().data
            or []
        )
        reached = reached_positions(games)
        keys = sorted(reached)
        evals: dict[str, list[dict]] = {}
        for start in range(0, len(keys), CHUNK):
            for row in (
                sb.table("position_evals").select("fen_key, lines").in_("fen_key", keys[start : start + CHUNK]).eq("nodes", settings.analysis_nodes).execute().data
                or []
            ):
                evals[row["fen_key"]] = row.get("lines") or []
        traps = []
        for key, entry in reached.items():
            found = score_trap(entry, evals.get(key, []))
            if found:
                traps.append((key, entry, found))
        traps.sort(key=lambda t: (-likely_rate(t[2]["caught"], t[1]["seen"]), -t[2]["caught"]))
        now = datetime.now(timezone.utc).isoformat()
        rows = [
            {
                "user_id": owner_id, "fen": e["fen"], "fen_key": k, "line": e["line"], "user_move": e["move"], "seen": e["seen"],
                "caught": f["caught"], "rate": f["rate"], "gain_cp": f["gain_cp"], "slip": f["slip"], "defence": f["defence"], "computed_at": now,
            }
            for k, e, f in traps[:TOP]
        ]
        sb.table("traps_set").delete().eq("user_id", owner_id).execute()
        if rows:
            sb.table("traps_set").insert(rows).execute()
        return {"traps": len(rows), "positions": len(reached)}

    def get(self, owner_id: str) -> list[dict]:
        rows = get_supabase().table("traps_set").select("*").eq("user_id", owner_id).execute().data or []
        return sorted((to_api(r) for r in rows), key=lambda t: (-t["likely"], -t["caught"]))
