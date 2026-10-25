"""Populate speed-routed human probabilities for a resumable, optionally frozen game snapshot."""

from __future__ import annotations

import argparse
import io
import json
from datetime import datetime, timezone
from pathlib import Path

import chess.pgn

from app.config import settings
from app.db.supabase import get_supabase
from app.services.human_model import SupabaseProbStore, cached_move_probs, elo_ladder, get_human_model_for_game
from app.services.library import boards_before
from app.services.position_evals import fen_key, iter_live_positions
from app.services.rating_map import opponent_model_elo

PAGE = 1000


def complete_games(limit: int = 0) -> list[dict]:
    rows: list[dict] = []
    while not limit or len(rows) < limit:
        size = min(PAGE, limit - len(rows)) if limit else PAGE
        batch = (
            get_supabase().table("games")
            .select("id, pgn, user_color, opponent_rating, source, time_control")
            .eq("analysis_status", "complete").order("played_at").order("id")
            .range(len(rows), len(rows) + size - 1).execute().data or []
        )
        rows.extend(batch)
        if len(batch) < size:
            break
    return rows


def write_snapshot(path: Path, games: list[dict]) -> None:
    payload = {
        "capturedAt": datetime.now(timezone.utc).isoformat(),
        "gameCount": len(games),
        "gameIds": [game["id"] for game in games],
    }
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def snapshot_ids(path: Path) -> set[str]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return set(payload["gameIds"] if isinstance(payload, dict) else payload)


def positions(game: dict, classified: list[dict]):
    parsed = chess.pgn.read_game(io.StringIO(game.get("pgn") or ""))
    if parsed is None:
        return []
    board, moves = parsed.board(), list(parsed.mainline_moves())
    out = [board.copy() for board, _move in boards_before(game["pgn"])]
    out.extend(
        position.copy()
        for _ply, position in iter_live_positions(
            board, moves, game.get("user_color") or "white", classified
        )
    )
    return list({fen_key(position): position for position in out}.values())


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    selection = parser.add_mutually_exclusive_group()
    selection.add_argument("--limit", type=int, default=0)
    selection.add_argument("--all", action="store_true", help="Explicitly select every complete game")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--prewarm", action="store_true", help="Load and validate both Maia checkpoints first")
    parser.add_argument("--snapshot", type=Path, help="Only IDs in an existing snapshot manifest")
    parser.add_argument("--write-snapshot", type=Path, help="Atomically freeze the selected game IDs")
    args = parser.parse_args()

    if args.prewarm:
        import chess

        for checkpoint in ("blitz", "rapid"):
            model = get_human_model_for_game(
                "maia2", {"source": "chess_com", "time_control": "60" if checkpoint == "blitz" else "600"}
            )
            board = chess.Board()
            probs = model.move_probs(board, 1600)
            if set(probs) != {move.uci() for move in board.legal_moves} or abs(sum(probs.values()) - 1) > 1e-6:
                raise RuntimeError(f"{checkpoint} checkpoint returned an invalid distribution")
            print(f"prewarmed={model.model_version}")

    games = complete_games(args.limit)
    if args.snapshot:
        allowed = snapshot_ids(args.snapshot)
        games = [game for game in games if game["id"] in allowed]
    if args.write_snapshot:
        write_snapshot(args.write_snapshot, games)
    print(f"games={len(games)} dry_run={args.dry_run}")
    if args.dry_run:
        return 0

    sb, store, failed, computed = get_supabase(), SupabaseProbStore(), 0, 0
    for index, game in enumerate(games, 1):
        classified = (
            sb.table("game_moves").select("ply, eval_before, eval_after")
            .eq("game_id", game["id"]).order("ply").execute().data or []
        )
        try:
            model = get_human_model_for_game(settings.human_model, game)
            for position in positions(game, classified):
                for elo in elo_ladder(opponent_model_elo(game)):
                    cached_move_probs(position, elo, model, store)
                    computed += 1
        except Exception as exc:
            failed += 1
            print(f"{game['id']}: {type(exc).__name__}: {str(exc)[:160]}", flush=True)
        if index % 25 == 0:
            print(f"{index}/{len(games)} games, lookups={computed}, failed={failed}", flush=True)
    print(f"done={len(games) - failed} failed={failed} lookups={computed}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
