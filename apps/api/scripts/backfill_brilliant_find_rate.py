"""
Apply the Brilliant find-rate rule (ADR 0004) to games already analysed.

    python -m scripts.backfill_brilliant_find_rate --limit 50
    python -m scripts.backfill_brilliant_find_rate --dry-run

Only games whose style vector is not yet version 2 are touched. The human model is used through the
`human_probs` cache, so games that went through the Chaos Lens pass need no new model calls.
"""

from __future__ import annotations

import argparse
import asyncio

from app.db.supabase import get_supabase
from app.services.baseline import BaselineService
from app.services.brilliant_find_rate import VERSION, BrilliantFindRate


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--dry-run", action="store_true", help="List the games without changing them")
    args = parser.parse_args()

    rows = (
        get_supabase()
        .table("games")
        .select("id, user_id, chess_com_username, game_analyses(style_vector)")
        .eq("analysis_status", "complete")
        .order("played_at", desc=True)
        .limit(args.limit)
        .execute()
        .data
        or []
    )
    todo = []
    for row in rows:
        a = row.get("game_analyses")
        vector = (a[0] if isinstance(a, list) and a else a or {}).get("style_vector") or {}
        if vector.get("version") != VERSION:
            todo.append(row)
    print(f"{len(todo)} of {len(rows)} games need the find-rate rule")
    if args.dry_run:
        return
    service, demoted, users = BrilliantFindRate(), 0, set()
    for row in todo:
        result = service.apply(row["id"]) or {}
        demoted += result.get("demoted", 0)
        users.add((row.get("user_id"), row.get("chess_com_username")))
        print(f"  {row['id']}: {result.get('demoted', 0)} demoted, Brilliant {result.get('brilliantPct')}%")
    for user_id, username in users:
        asyncio.run(BaselineService().recompute_baseline(user_id=user_id, chess_com_username=username))
    print(f"Done: {demoted} moves no longer Brilliant across {len(todo)} games")


if __name__ == "__main__":
    main()
