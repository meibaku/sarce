"""Populate speed-routed human probabilities for a resumable, optionally frozen game snapshot."""

from __future__ import annotations

import argparse
import io
import json
import time
from datetime import datetime, timezone
from pathlib import Path

import chess.pgn

from app.config import settings
from app.db.supabase import get_supabase
from app.services.human_model import TABLE, elo_ladder, get_human_model_for_game
from app.services.library import boards_before
from app.services.position_evals import fen_key, iter_live_positions
from app.services.rating_map import opponent_model_elo

PAGE = 1000
# Probability maps are wide JSON rows; small transactions stay under PostgREST's statement timeout
# even when several deterministic shards finish inference together.
WRITE_BATCH = 50


def execute(query, attempts: int = 5):
    """Retry transient local/PostgREST pressure; a permanent error still fails the run."""
    for attempt in range(attempts):
        try:
            return query.execute()
        except Exception:
            if attempt == attempts - 1:
                raise
            time.sleep(0.5 * (2**attempt))


def games(limit: int = 0, complete_only: bool = True) -> list[dict]:
    rows: list[dict] = []
    while not limit or len(rows) < limit:
        size = min(PAGE, limit - len(rows)) if limit else PAGE
        query = get_supabase().table("games").select(
            "id, pgn, user_color, opponent_rating, source, time_control"
        )
        if complete_only:
            query = query.eq("analysis_status", "complete")
        batch = execute(
            query.order("played_at").order("id").range(len(rows), len(rows) + size - 1)
        ).data or []
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


def existing_keys(model_version: str) -> set[tuple[str, int]]:
    """Read one checkpoint's cache identity in pages, avoiding a REST lookup per position."""
    rows: list[dict] = []
    while True:
        batch = (
            get_supabase().table(TABLE).select("fen_key, elo")
            .eq("model_version", model_version).range(len(rows), len(rows) + PAGE - 1)
        )
        batch = execute(batch).data or []
        rows.extend(batch)
        if len(batch) < PAGE:
            return {(row["fen_key"], int(row["elo"])) for row in rows}


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
    parser.add_argument("--batch-size", type=int, default=512, help="Maia inference batch size")
    parser.add_argument("--chunk-size", type=int, default=4096, help="Rows prepared per resumable work chunk")
    parser.add_argument("--shard-count", type=int, default=1, help="Split the fixed ordering into resumable shards")
    parser.add_argument("--shard-index", type=int, default=0, help="Zero-based shard to process")
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

    selected = games(args.limit)
    if args.snapshot:
        allowed = snapshot_ids(args.snapshot)
        selected = [game for game in selected if game["id"] in allowed]
    if args.shard_count < 1 or not 0 <= args.shard_index < args.shard_count:
        parser.error("--shard-index must be between zero and --shard-count minus one")
    selected = [
        game for index, game in enumerate(selected) if index % args.shard_count == args.shard_index
    ]
    if args.write_snapshot:
        # The acceptance manifest includes incomplete games too; they enter this backfill after retry succeeds.
        write_snapshot(args.write_snapshot, games(complete_only=False))
    print(f"games={len(selected)} dry_run={args.dry_run}")
    if args.dry_run:
        return 0

    sb, failed = get_supabase(), 0
    models: dict[str, object] = {}
    pending: dict[str, dict[tuple[str, int], str]] = {}
    for index, game in enumerate(selected, 1):
        classified = execute(
            sb.table("game_moves").select("ply, eval_before, eval_after")
            .eq("game_id", game["id"]).order("ply")
        ).data or []
        try:
            model = get_human_model_for_game(settings.human_model, game)
            models[model.model_version] = model
            jobs = pending.setdefault(model.model_version, {})
            for position in positions(game, classified):
                for elo in elo_ladder(opponent_model_elo(game)):
                    jobs.setdefault((fen_key(position), elo), position.fen())
        except Exception as exc:
            failed += 1
            print(f"{game['id']}: {type(exc).__name__}: {str(exc)[:160]}", flush=True)
        if index % 25 == 0:
            print(f"{index}/{len(selected)} games indexed, failed={failed}", flush=True)

    written = 0
    for version, jobs in pending.items():
        cached = existing_keys(version)
        missing = [(key, fen) for key, fen in jobs.items() if key not in cached]
        print(f"{version}: unique={len(jobs)} missing={len(missing)}", flush=True)
        model = models[version]
        for start in range(0, len(missing), args.chunk_size):
            part = missing[start : start + args.chunk_size]
            inputs = [(fen, key[1]) for key, fen in part]
            if hasattr(model, "move_probs_batch"):
                probabilities = model.move_probs_batch(inputs, args.batch_size)
            else:
                probabilities = [model.move_probs(chess.Board(fen), elo) for fen, elo in inputs]
            rows = [
                {"fen_key": key[0], "elo": key[1], "model_version": version, "probs": probs}
                for (key, _fen), probs in zip(part, probabilities) if probs
            ]
            for write_at in range(0, len(rows), WRITE_BATCH):
                execute(
                    sb.table(TABLE).upsert(
                        rows[write_at : write_at + WRITE_BATCH],
                        on_conflict="fen_key,elo,model_version",
                    )
                )
            written += len(rows)
            print(f"{version}: {min(start + len(part), len(missing))}/{len(missing)}", flush=True)
    print(f"done={len(selected) - failed} failed={failed} written={written}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
