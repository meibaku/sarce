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
from app.lenses import config as lens_config
from app.services.chaos_validation import clock_bucket, decider_clock_ms
from app.services.ep import cp_to_ep
from app.services.threats import THREAT_NODES
from app.services.rating_map import opponent_model_elo
from app.services.human_model import get_human_model_for_game
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


def mainline_ucis(pgn_text: str) -> list[str]:
    """UCI of every mainline ply."""
    game = chess.pgn.read_game(io.StringIO(pgn_text))
    return [] if game is None else [m.uci() for m in game.mainline_moves()]


def increment_ms(time_control: str | None) -> int:
    """Per-move increment in milliseconds from "180+2"; 0 when there is none or it can't be read."""
    try:
        return int(str(time_control).split("+")[1]) * 1000
    except (IndexError, TypeError, ValueError):
        return 0


def spent_on(clocks_ms: list[int | None], ply: int, initial_ms: int | None, inc_ms: int = 0) -> tuple[int | None, int | None]:
    """(clock before, time spent) for the move at `ply`. `%clk` is the mover's time after their own move."""
    before = (clocks_ms[ply - 2] if ply - 2 < len(clocks_ms) else None) if ply >= 2 else initial_ms
    after = clocks_ms[ply] if ply < len(clocks_ms) else None
    if before is None or after is None:
        return before, None
    return before, max(0, before - after + inc_ms)


def objective_cost(move: dict) -> float | None:
    """EP the mover gave up versus the engine's best move, from stored Phase 1 evals."""
    after, cp_loss = move.get("eval_after"), move.get("cp_loss")
    if after is None or cp_loss is None:
        return None
    played = cp_to_ep(float(after) * 100)
    best = cp_to_ep(float(after) * 100 + float(cp_loss))
    return round(max(0.0, best - played), 4)


def initial_clock_ms(time_control: str | None) -> int | None:
    """Starting clock in milliseconds from a time control like "60" or "180+2"."""
    try:
        return int(str(time_control).split("+")[0]) * 1000
    except (TypeError, ValueError):
        return None


def build_ply_contexts(
    pgn_text: str,
    move_rows: list[dict],
    evals_by_key: dict[str, dict],
    probs_by_key: dict[str, dict[int, dict[str, float]]],
    opponent_rating: int | None = None,
    clocks_ms: list[int | None] | None = None,
    initial_clock_ms: int | None = None,
    model_name: str | None = None,
    inc_ms: int = 0,
    threats_by_key: dict[str, dict] | None = None,
) -> list[tuple[dict, PlyContext]]:
    """Pair every stored user move with its context. Pure: no I/O."""
    keys = keys_after_each_ply(pgn_text)
    ucis = mainline_ucis(pgn_text)
    multipliers = lens_config.CLOCK_MULTIPLIERS.get(model_name or "", {})

    def position(ply: int) -> PositionData | None:
        if not 0 <= ply < len(keys) or keys[ply] not in evals_by_key:
            return None
        row = evals_by_key[keys[ply]]
        # The clock that matters is the replier's, when they start thinking about this position.
        bucket = clock_bucket(decider_clock_ms(clocks_ms or [], ply, initial_clock_ms))
        return PositionData(
            lines=row.get("lines") or [],
            safe_set_complete=bool(row.get("safe_set_complete")),
            probs_by_elo=probs_by_key.get(keys[ply], {}),
            clock_bucket=bucket,
            p_fail_multiplier=multipliers.get(bucket, 1.0),
            key=keys[ply],
            threat=(threats_by_key or {}).get(keys[ply]),
        )

    contexts = []
    for move in sorted(move_rows, key=lambda m: m["ply"]):
        before = move.get("eval_before")
        clock, spent = spent_on(clocks_ms or [], move["ply"], initial_clock_ms, inc_ms)
        ctx = PlyContext(
            ply=move["ply"],
            uci=move["uci"],
            quality=move.get("quality"),
            ep_before=None if before is None else cp_to_ep(float(before) * 100),
            objective_cost=objective_cost(move),
            faced=position(move["ply"] - 1),
            left=position(move["ply"]),
            opponent_elo=opponent_rating,
            reply_uci=ucis[move["ply"] + 1] if move["ply"] + 1 < len(ucis) else None,
            clock_ms=clock,
            spent_ms=spent,
            initial_ms=initial_clock_ms,
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


def rank_chaos_games(peaks: list[dict], verdicts: list[dict], limit: int) -> list[dict]:
    """
    Games by their peak chaos score, highest first, with verdict counts.

    `peaks` are chaos-lens rows (`game_id`, `score`) in descending score order, so the first row seen per game is
    its peak; `verdicts` are those games' rows (`game_id`, `verdict`). Ties keep more real chaos first.
    """
    games: dict[str, dict] = {}
    for row in peaks:
        if row["game_id"] not in games:
            games[row["game_id"]] = {"gameId": row["game_id"], "chaosPeak": float(row.get("score") or 0.0), "realChaos": 0, "cheapChaos": 0, "calculatedRisk": 0}
    for row in verdicts:
        point = games.get(row["game_id"])
        if point:
            verdict = row.get("verdict")
            point["realChaos"] += verdict == "real_chaos"
            point["cheapChaos"] += verdict == "cheap_chaos"
            point["calculatedRisk"] += verdict == "calculated_risk"
    return sorted(games.values(), key=lambda g: (-g["chaosPeak"], -g["realChaos"], g["gameId"]))[:limit]


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
            .select("id, pgn, opponent_rating, source, clocks_ms, time_control")
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
        model = get_human_model_for_game(settings.human_model, game.data)
        model_version = model.model_version
        probs = self._fetch_by_keys("human_probs", keys, "model_version", model_version)
        threats = self._fetch_by_keys("position_threats", keys, "nodes", THREAT_NODES)

        probs_by_key: dict[str, dict[int, dict[str, float]]] = {}
        for row in probs:
            probs_by_key.setdefault(row["fen_key"], {})[int(row["elo"])] = row["probs"]

        contexts = build_ply_contexts(
            game.data["pgn"],
            moves,
            {row["fen_key"]: row for row in evals},
            probs_by_key,
            opponent_model_elo(game.data),  # the human model's scale (review F1)
            clocks_ms=game.data.get("clocks_ms"),
            initial_clock_ms=initial_clock_ms(game.data.get("time_control")),
            inc_ms=increment_ms(game.data.get("time_control")),
            threats_by_key={row["fen_key"]: row for row in threats},
            model_name=model.name,
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

    def most_chaotic_games(self, user_id: str | None = None, username: str | None = None, limit: int = 20) -> list[dict]:
        """
        A player's chaos-analysed games, most chaotic first. Reads the highest-scoring chaos rows in score order
        (so the first row per game is its peak) until `limit` games are found, instead of every row of a full
        history, then counts verdicts for just those games.
        """
        sb = get_supabase()
        peaks: list[dict] = []
        seen: set[str] = set()
        page = 1000  # PostgREST's response cap
        while len(seen) < limit:
            query = sb.table(TABLE).select("game_id, score, games!inner(user_id, chess_com_username)").eq("lens", "chaos")
            if user_id:
                query = query.eq("games.user_id", user_id)
            if username:
                query = query.eq("games.chess_com_username", username)
            batch = query.order("score", desc=True).order("game_move_id").range(len(peaks), len(peaks) + page - 1).execute().data or []
            peaks.extend(batch)
            seen.update(r["game_id"] for r in batch)
            if len(batch) < page:
                break
        top = list(dict.fromkeys(r["game_id"] for r in peaks))[:limit]
        verdicts: list[dict] = []
        for start in range(0, len(top), 10):  # ~40 chaos rows a game: stays under the 1000-row cap
            verdicts += sb.table(TABLE).select("game_id, verdict").in_("game_id", top[start : start + 10]).eq("lens", "chaos").limit(page).execute().data or []
        return rank_chaos_games([r for r in peaks if r["game_id"] in set(top)], verdicts, limit)

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
