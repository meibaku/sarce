"""
Brilliant % under the current rules (v3) for a reference player and for you, with a game-level interval and the
clause that stops each near-miss (review F6).

A reference game goes through exactly the pipeline a player's game does: one shared engine search per position
(`game_lines`, the app's node budget), classification, then the find-rate (ADR 0004) and real-offer (ADR 0007)
post-pass at the rung nearest the opponent's rating. Games the player isn't in are skipped, never guessed.

The interval is a bootstrap over whole games: Brilliant moves cluster within games, so resampling moves would
overstate certainty.
"""

from __future__ import annotations

import io
import random
from collections import Counter

import chess
import chess.pgn

from app.services.brilliant import CLAUSES, brilliant_clauses
from app.services.brilliant_find_rate import apply_rule, rung_for
from app.services.move_classifier import MoveClassifier
from app.services.position_evals import game_lines
from app.services.reference import _matches_player_name

BOOTSTRAP_ITERS = 2000


class MemoryEvalStore:
    """In-memory `position_evals` for a one-off run (nothing written to the database)."""

    def __init__(self) -> None:
        self.rows: dict[str, dict] = {}

    def get(self, key: str, nodes: int) -> dict | None:
        row = self.rows.get(key)
        return row if row and row["nodes"] == nodes else None

    def put(self, row: dict) -> None:
        self.rows[row["fen_key"]] = row


def player_color(game: chess.pgn.Game, player: str) -> str | None:
    if _matches_player_name(game.headers.get("White", ""), player):
        return "white"
    if _matches_player_name(game.headers.get("Black", ""), player):
        return "black"
    return None


def first_failure(clauses: dict[str, bool | None]) -> str | None:
    """The first clause, in CLAUSES order, that is False; None when none fails."""
    return next((c for c in CLAUSES if clauses.get(c) is False), None)


def benchmark_game(pgn_text: str, player: str, engine, model) -> dict | None:
    """
    One reference game through the app's pipeline: {moves, brilliant, candidates, stopped_by}. `candidates` are moves
    that genuinely offered a piece; `stopped_by` counts the first clause that failed for each of them.
    """
    game = chess.pgn.read_game(io.StringIO(pgn_text))
    if game is None:
        return None
    color = player_color(game, player)
    if color is None:
        return None
    board, moves = game.board(), list(game.mainline_moves())
    lines = game_lines(board, moves, engine, MemoryEvalStore())
    classified = MoveClassifier().classify_game(board, moves, color, lines=lines)
    raw = game.headers.get("BlackElo" if color == "white" else "WhiteElo", "")
    elo = rung_for(int(raw) if raw.isdigit() else None)

    boards: list[chess.Board] = []
    temp = board.copy()
    for move in moves:
        boards.append(temp.copy(stack=False))
        temp.push(move)

    probs_cache: dict[int, dict] = {}

    def probs_for(ply: int):
        if ply not in probs_cache:
            probs_cache[ply] = model.move_probs(boards[ply], elo)
        return probs_cache[ply]

    updated, _ = apply_rule(classified, probs_for)
    stopped: Counter[str] = Counter()
    candidates = 0
    for m in updated:
        ply = m["ply"]
        move = chess.Move.from_uci(m["uci"])
        best_eval = None if m.get("eval_after") is None else m["eval_after"] + (m.get("cp_loss") or 0) / 100
        clauses = brilliant_clauses(boards[ply], move, m.get("eval_before"), m.get("eval_after"), best_eval)
        if not clauses["real_sacrifice"]:
            continue
        candidates += 1
        if all(clauses[c] for c in CLAUSES[:4]):
            clauses["hard_to_find"] = None if m.get("is_brilliant") else False
        failed = first_failure(clauses)
        stopped[failed or "brilliant"] += 1
    return {
        "moves": len(updated),
        "brilliant": sum(1 for m in updated if m.get("is_brilliant")),
        "candidates": candidates,
        "stopped_by": dict(stopped),
        "elo": elo,
        "qualities": dict(Counter(m["quality"] for m in updated)),
    }


def pooled_pct(per_game: list[tuple[int, int]]) -> float | None:
    moves = sum(n for _, n in per_game)
    return None if not moves else 100 * sum(b for b, _ in per_game) / moves


def bootstrap_interval(per_game: list[tuple[int, int]], iters: int = BOOTSTRAP_ITERS, seed: int = 7) -> tuple[float, float] | None:
    """95% interval for the pooled Brilliant %, resampling whole games (brilliant, moves)."""
    if not per_game:
        return None
    rng = random.Random(seed)
    samples = sorted(pooled_pct([rng.choice(per_game) for _ in per_game]) or 0.0 for _ in range(iters))
    return samples[int(0.025 * iters)], samples[int(0.975 * iters) - 1]


def summarize(results: list[dict]) -> dict:
    """Pooled Brilliant %, its game-level interval, and where the near-misses stop."""
    per_game = [(r["brilliant"], r["moves"]) for r in results]
    stopped: Counter[str] = Counter()
    for r in results:
        stopped.update(r["stopped_by"])
    pct = pooled_pct(per_game)
    interval = bootstrap_interval(per_game)
    return {
        "games": len(results),
        "moves": sum(n for _, n in per_game),
        "brilliant": sum(b for b, _ in per_game),
        "brilliantPct": None if pct is None else round(pct, 2),
        "interval": None if interval is None else [round(interval[0], 2), round(interval[1], 2)],
        "candidates": sum(r["candidates"] for r in results),
        "stoppedBy": dict(stopped.most_common()),
    }


def player_report(owner_id: str, games_read: int = 2000) -> dict:
    """
    The same summary for your analysed games, from stored data: Brilliant % with its game-level interval, and the
    first clause that stopped each of your real sacrifices. No engine; human-model probabilities come from the cache.
    """
    from app.config import settings
    from app.db.supabase import get_supabase
    from app.services.human_model import SupabaseProbStore, cached_move_probs, get_human_model
    from app.services.library import boards_before

    sb = get_supabase()
    games = (
        sb.table("games").select("id, pgn, opponent_rating").eq("user_id", owner_id).eq("analysis_status", "complete")
        .neq("source", "sarce_bot").order("played_at", desc=True).limit(games_read).execute().data
        or []
    )
    model, store = get_human_model(settings.human_model), SupabaseProbStore()
    results = []
    for start in range(0, len(games), 100):
        part = games[start : start + 100]
        moves: list[dict] = []
        while True:  # paged: PostgREST caps a response at 1,000 rows
            batch = (
                sb.table("game_moves").select("game_id, ply, uci, eval_before, eval_after, cp_loss, is_brilliant, signals")
                .in_("game_id", [g["id"] for g in part]).order("id").range(len(moves), len(moves) + 999).execute().data
                or []
            )
            moves += batch
            if len(batch) < 1000:
                break
        by_game: dict[str, list[dict]] = {}
        for m in moves:
            by_game.setdefault(m["game_id"], []).append(m)
        for g in part:
            mine = by_game.get(g["id"], [])
            if not mine:
                continue
            stopped: Counter[str] = Counter()
            candidates = [m for m in mine if "real_sacrifice" in (m.get("signals") or [])]
            plies = boards_before(g.get("pgn") or "") if candidates else []
            elo = rung_for(g.get("opponent_rating"))
            for m in candidates:
                if m["ply"] >= len(plies):
                    continue
                board, move = plies[m["ply"]]
                best_eval = None if m.get("eval_after") is None else m["eval_after"] + (m.get("cp_loss") or 0) / 100
                clauses = brilliant_clauses(board, move, m.get("eval_before"), m.get("eval_after"), best_eval)
                if all(clauses[c] for c in CLAUSES[:4]):
                    clauses["hard_to_find"] = brilliant_clauses(
                        board, move, m["eval_before"], m["eval_after"], best_eval, cached_move_probs(board, elo, model, store)
                    )["hard_to_find"]
                stopped[first_failure(clauses) or "brilliant"] += 1
            results.append({"moves": len(mine), "brilliant": sum(1 for m in mine if m.get("is_brilliant")), "candidates": len(candidates), "stopped_by": dict(stopped)})
    return summarize(results)
