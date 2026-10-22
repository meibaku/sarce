"""
Store threats (null-move searches) for games analysed before the prophylaxis lens, then re-score their lenses.

Usage:
    cd apps/api
    python -m scripts.backfill_threats [--limit 0] [--workers 2]

Needs a local Stockfish (one short search per position the user faced). Newest games first; positions already in
`position_threats` are skipped, so the script can be re-run after an interruption.
"""

from __future__ import annotations

import argparse
import io
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import chess.pgn

# Allow running as script from apps/api
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db.supabase import get_supabase
from app.services.lens_service import LensService
from app.services.stockfish import StockfishEngine
from app.services.threats import SupabaseThreatStore, evaluate_game_threats

PAGE = 1000


def game_rows(limit: int) -> list[dict]:
    sb = get_supabase()
    rows: list[dict] = []
    while True:
        batch = (
            sb.table("games").select("id, pgn, user_color").eq("analysis_status", "complete").neq("source", "sarce_bot")
            .order("played_at", desc=True).range(len(rows), len(rows) + PAGE - 1).execute().data
            or []
        )
        rows += batch
        if len(batch) < PAGE or (limit and len(rows) >= limit):
            break
    return rows[:limit] if limit else rows


def one(game: dict) -> str:
    parsed = chess.pgn.read_game(io.StringIO(game.get("pgn") or ""))
    if parsed is None:
        return "skipped"
    moves = list(parsed.mainline_moves())
    classified = get_supabase().table("game_moves").select("ply, eval_before, eval_after").eq("game_id", game["id"]).execute().data or []
    if not classified:
        return "skipped"
    with StockfishEngine() as engine:
        evaluate_game_threats(parsed.board(), moves, game.get("user_color") or "white", classified, engine, SupabaseThreatStore())
    LensService().score_game(game["id"])
    return "done"


def main(limit: int, workers: int) -> None:
    games = game_rows(limit)
    done = failed = 0
    with ThreadPoolExecutor(max_workers=workers) as pool:
        for n, result in enumerate(pool.map(lambda g: _safe(g), games), 1):
            done += result == "done"
            failed += result == "failed"
            if n % 25 == 0:
                print(f"{n}/{len(games)} games ({failed} failed)", flush=True)
    print(f"Done: {done} games with threats stored and lenses re-scored, {failed} failed.")


def _safe(game: dict) -> str:
    try:
        return one(game)
    except Exception as exc:  # one bad game must not stop the run
        print(f"  {game['id']}: {exc}", flush=True)
        return "failed"


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Backfill threats for the prophylaxis lens")
    parser.add_argument("--limit", type=int, default=0, help="Games (0 = all)")
    parser.add_argument("--workers", type=int, default=2, help="Parallel engines")
    args = parser.parse_args()
    main(args.limit, args.workers)
