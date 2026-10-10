"""
Lens scoring — builds each move's context from stored data and persists lens results.

No engine or human-model calls happen here (docs/CHAOS_PLAN.md, rule 3): scoring a game
again, or adding a lens, only re-reads `position_evals` and `human_probs`.
"""

from __future__ import annotations

import io

import chess
import chess.pgn

from app.config import settings
from app.db.supabase import get_supabase
from app.lenses import PlyContext, PositionData, score_ply
from app.services.ep import cp_to_ep
from app.services.human_model import get_human_model
from app.services.position_evals import fen_key

TABLE = "move_lens_scores"
CHUNK = 40  # FEN keys per `in` filter, to keep request URLs short
CHAOS_VERDICTS = ("real_chaos", "cheap_chaos", "calculated_risk")


def keys_after_each_ply(pgn_text: str) -> list[str]:
    """Cache key of the position after every mainline ply."""
    game = chess.pgn.read_game(io.StringIO(pgn_text))
    if game is None:
        return []
    board, keys = game.board(), []
    for move in game.mainline_moves():
        board.push(move)
        keys.append(fen_key(board))
    return keys


def objective_cost(move: dict) -> float | None:
    """EP the mover gave up versus the engine's best move, from stored Phase 1 evals."""
    after, cp_loss = move.get("eval_after"), move.get("cp_loss")
    if after is None or cp_loss is None:
        return None
    played = cp_to_ep(float(after) * 100)
    best = cp_to_ep(float(after) * 100 + float(cp_loss))
    return round(max(0.0, best - played), 4)


def build_ply_contexts(
    pgn_text: str,
    move_rows: list[dict],
    evals_by_key: dict[str, dict],
    probs_by_key: dict[str, dict[int, dict[str, float]]],
    opponent_rating: int | None = None,
) -> list[tuple[dict, PlyContext]]:
    """Pair every stored user move with its context. Pure: no I/O."""
    keys = keys_after_each_ply(pgn_text)

    def position(ply: int) -> PositionData | None:
        if not 0 <= ply < len(keys) or keys[ply] not in evals_by_key:
            return None
        row = evals_by_key[keys[ply]]
        return PositionData(
            lines=row.get("lines") or [],
            safe_set_complete=bool(row.get("safe_set_complete")),
            probs_by_elo=probs_by_key.get(keys[ply], {}),
        )

    contexts = []
    for move in sorted(move_rows, key=lambda m: m["ply"]):
        before = move.get("eval_before")
        ctx = PlyContext(
            ply=move["ply"],
            uci=move["uci"],
            quality=move.get("quality"),
            ep_before=None if before is None else cp_to_ep(float(before) * 100),
            objective_cost=objective_cost(move),
            faced=position(move["ply"] - 1),
            left=position(move["ply"]),
            opponent_elo=opponent_rating,
        )
        contexts.append((move, ctx))
    return contexts


def score_contexts(game_id: str, contexts: list[tuple[dict, PlyContext]]) -> list[dict]:
    """Run the lens registry over built contexts and return `move_lens_scores` rows."""
    rows = []
    for move, ctx in contexts:
        for name, (lens, result) in score_ply(ctx).items():
            rows.append(
                {
                    "game_id": game_id,
                    "game_move_id": move["id"],
                    "ply": ctx.ply,
                    "lens": name,
                    "lens_version": lens.version,
                    "score": result.score,
                    "verdict": result.verdict,
                    "details": result.details,
                }
            )
    return rows


def summarize(rows: list[dict]) -> dict:
    """Counts of chaos verdicts and the survival rate from stored lens rows."""
    chaos = {v: 0 for v in CHAOS_VERDICTS}
    survived = missed = 0
    for row in rows:
        verdict = row.get("verdict")
        if row.get("lens") == "chaos" and verdict in chaos:
            chaos[verdict] += 1
        elif row.get("lens") == "survival":
            survived += verdict == "survived"
            missed += verdict == "missed"
    faced = survived + missed
    return {
        "realChaos": chaos["real_chaos"],
        "cheapChaos": chaos["cheap_chaos"],
        "calculatedRisk": chaos["calculated_risk"],
        "problemsFaced": faced,
        "survived": survived,
        "survivalRate": round(survived / faced, 4) if faced else None,
    }


def per_game_chaos(rows: list[dict]) -> list[dict]:
    """Real and cheap chaos counts per game, oldest first, for the dashboard trend."""
    games: dict[str, dict] = {}
    for row in rows:
        if row.get("lens") != "chaos" or "game_id" not in row:
            continue
        played_at = (row.get("games") or {}).get("played_at")
        point = games.setdefault(
            row["game_id"],
            {"gameId": row["game_id"], "playedAt": played_at, "realChaos": 0, "cheapChaos": 0},
        )
        point["realChaos"] += row.get("verdict") == "real_chaos"
        point["cheapChaos"] += row.get("verdict") == "cheap_chaos"
    return sorted(games.values(), key=lambda g: g["playedAt"] or "")


class LensService:
    """Supabase-backed loading, scoring and reading of lens results."""

    def _fetch_by_keys(self, table: str, keys: list[str], column: str, value) -> list[dict]:
        rows: list[dict] = []
        unique = sorted(set(keys))
        for start in range(0, len(unique), CHUNK):
            res = (
                get_supabase()
                .table(table)
                .select("*")
                .in_("fen_key", unique[start : start + CHUNK])
                .eq(column, value)
                .execute()
            )
            rows.extend(res.data or [])
        return rows

    def score_game(self, game_id: str) -> list[dict] | None:
        """Re-score one game from stored raw data. Returns the rows, or None if the game is unknown."""
        sb = get_supabase()
        game = (
            sb.table("games")
            .select("id, pgn, opponent_rating")
            .eq("id", game_id)
            .maybe_single()
            .execute()
        )
        if not game or not game.data:
            return None
        moves = (
            sb.table("game_moves")
            .select("id, ply, uci, quality, cp_loss, eval_before, eval_after")
            .eq("game_id", game_id)
            .execute()
        ).data or []

        keys = keys_after_each_ply(game.data["pgn"])
        evals = self._fetch_by_keys("position_evals", keys, "nodes", settings.analysis_nodes)
        model_version = get_human_model(settings.human_model).model_version
        probs = self._fetch_by_keys("human_probs", keys, "model_version", model_version)

        probs_by_key: dict[str, dict[int, dict[str, float]]] = {}
        for row in probs:
            probs_by_key.setdefault(row["fen_key"], {})[int(row["elo"])] = row["probs"]

        contexts = build_ply_contexts(
            game.data["pgn"],
            moves,
            {row["fen_key"]: row for row in evals},
            probs_by_key,
            game.data.get("opponent_rating"),
        )
        rows = score_contexts(game_id, contexts)
        # Replace, so a lens that no longer fires does not leave a stale row behind.
        sb.table(TABLE).delete().eq("game_id", game_id).execute()
        if rows:
            sb.table(TABLE).insert(rows).execute()
        return rows

    def get_game_lenses(self, game_id: str) -> list[dict]:
        """Stored lens results for a game, grouped per move."""
        res = get_supabase().table(TABLE).select("*").eq("game_id", game_id).order("ply").execute()
        by_ply: dict[int, dict] = {}
        for row in res.data or []:
            entry = by_ply.setdefault(row["ply"], {"ply": row["ply"], "lenses": {}})
            entry["lenses"][row["lens"]] = {
                "version": row["lens_version"],
                "score": None if row["score"] is None else float(row["score"]),
                "verdict": row["verdict"],
                "details": row["details"],
            }
        return [by_ply[ply] for ply in sorted(by_ply)]

    def get_game_clocks(self, game_id: str) -> list | None:
        """Per-ply clocks for a game; None when missing or the column is not migrated yet."""
        try:
            res = (
                get_supabase().table("games").select("clocks_ms").eq("id", game_id).limit(1).execute()
            )
        except Exception:
            return None
        return res.data[0].get("clocks_ms") if res.data else None

    def chaos_summary(self, username: str, user_id: str | None = None) -> dict:
        """Chaos counts for a username; `user_id` (the signed-in caller) narrows it to their games."""
        query = (
            get_supabase()
            .table(TABLE)
            .select("game_id, lens, verdict, games!inner(chess_com_username, played_at, user_id)")
            .eq("games.chess_com_username", username)
            .in_("lens", ["chaos", "survival"])
        )
        if user_id:
            query = query.eq("games.user_id", user_id)
        res = query.execute()
        rows = res.data or []
        return {"username": username, **summarize(rows), "perGame": per_game_chaos(rows)}
