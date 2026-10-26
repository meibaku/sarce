"""Build, annotate and qualify the LE2 piece-safety bank. Run from `apps/api`."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Allow `python scripts/piece_safety_bank.py` from apps/api, matching the other maintenance scripts.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import settings
from app.db.supabase import get_supabase
from app.services.ep import cp_to_ep
from app.services.library import boards_before
from app.services.pattern_review import review_report
from app.services.patterns import CONCEPT, PatternStore, TABLE
from app.services.piece_safety import candidate_after_move
from app.services.position_evals import fen_key


def build_game(game_id: str, review_set: str) -> dict:
    """Create reviewer candidates from a completed game's stored moves and fixed-node searches."""
    sb = get_supabase()
    games = sb.table("games").select("id,user_id,pgn,analysis_status").eq("id", game_id).limit(1).execute().data or []
    if not games or games[0].get("analysis_status") != "complete":
        raise ValueError("game must exist and have complete analysis")
    game = games[0]
    positions = boards_before(game.get("pgn") or "")
    moves = sb.table("game_moves").select("ply,uci,eval_before").eq("game_id", game_id).order("ply").execute().data or []
    created = {"positive": 0, "near_miss": 0, "control": 0, "skipped": 0}
    store = PatternStore()
    for row in moves:
        ply = int(row["ply"])
        if ply >= len(positions) or row.get("eval_before") is None:
            created["skipped"] += 1
            continue
        board, played = positions[ply]
        after = board.copy()
        after.push(played)
        evaluations = (
            sb.table("position_evals").select("*").eq("fen_key", fen_key(after)).eq("nodes", settings.analysis_nodes).limit(1).execute().data or []
        )
        if not evaluations:
            created["skipped"] += 1
            continue
        candidate = candidate_after_move(
            board_before=board,
            played=played,
            player_ep_before=cp_to_ep(float(row["eval_before"]) * 100),
            evaluation=evaluations[0],
            owner_id=game["user_id"],
            game_id=game_id,
            ply=ply,
        )
        if candidate is None:
            created["skipped"] += 1
            continue
        candidate["review_set"] = review_set
        saved = store.put_candidate(candidate)
        created[saved["label"]] += 1
    return created


def rows(review_set: str | None = None) -> list[dict]:
    query = get_supabase().table(TABLE).select("*").eq("concept_key", CONCEPT).order("created_at")
    if review_set:
        query = query.eq("review_set", review_set)
    return query.execute().data or []


def main() -> int:
    parser = argparse.ArgumentParser(description="LE2 piece-safety bank reviewer")
    commands = parser.add_subparsers(dest="command", required=True)
    build = commands.add_parser("build-game")
    build.add_argument("game_id")
    build.add_argument("--review-set", choices=("calibration", "heldout"), default="calibration")
    listing = commands.add_parser("list")
    listing.add_argument("--review-set", choices=("calibration", "heldout"))
    annotate = commands.add_parser("annotate")
    annotate.add_argument("pattern_id")
    annotate.add_argument("--reviewer", required=True)
    annotate.add_argument("--decision", choices=("approve", "reject", "unclear"), required=True)
    annotate.add_argument("--note", default="")
    decide = commands.add_parser("decide")
    decide.add_argument("pattern_id")
    decide.add_argument("--status", choices=("approved", "rejected", "retired"), required=True)
    family = commands.add_parser("family")
    family.add_argument("pattern_id")
    family.add_argument("--key", required=True, help="Shared structural family; prevents train/test leakage")
    report = commands.add_parser("report")
    report.add_argument("--require-ready", action="store_true")
    args = parser.parse_args()
    store = PatternStore()
    if args.command == "build-game":
        out = build_game(args.game_id, args.review_set)
    elif args.command == "list":
        out = [{
            "id": row["id"], "set": row.get("review_set"), "status": row["review_status"], "label": row["label"],
            "fen": row["position_fen"], "target": row["target"], "verification": row["verification"],
            "annotations": row["review_annotations"],
        } for row in rows(args.review_set)]
    elif args.command == "annotate":
        out = store.annotate(args.pattern_id, args.reviewer, args.decision, args.note)
    elif args.command == "decide":
        out = store.set_status(args.pattern_id, args.status)
    elif args.command == "family":
        key = args.key.strip()[:200]
        if not key:
            raise ValueError("family key is required")
        out = get_supabase().table(TABLE).update({"family_key": key}).eq("id", args.pattern_id).execute().data[0]
    else:
        out = review_report(rows("heldout"))
        if args.require_ready and not out["autoServeReady"]:
            print(json.dumps(out, indent=2, sort_keys=True))
            return 1
    print(json.dumps(out, indent=2, sort_keys=True, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
