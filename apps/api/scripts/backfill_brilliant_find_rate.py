"""
Apply the current Brilliant rule (v4, ADR 0009, with the find-rate clause of ADR 0004) to games already analysed.

    python -m scripts.backfill_brilliant_find_rate            # every game not yet on the current version
    python -m scripts.backfill_brilliant_find_rate --limit 50
    python -m scripts.backfill_brilliant_find_rate --dry-run

Only games whose style vector is not yet the current version are touched. Every move is judged from scratch from
stored data (no engine); the human model is used through the `human_probs` cache, computing a miss only for moves
that pass the board clauses.
"""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

from app.db.supabase import get_supabase
from app.services.baseline import BaselineService
from app.services.brilliant_find_rate import VERSION, BrilliantFindRate


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    parser.add_argument("--limit", type=int, default=0, help="Games to read (0 = all)")
    parser.add_argument("--dry-run", action="store_true", help="List the games without changing them")
    parser.add_argument("--all", action="store_true", help="Re-judge every game, even those on the current version")
    parser.add_argument("--snapshot", type=Path, help="Only game IDs in this fixed manifest")
    args = parser.parse_args()

    rows: list[dict] = []
    while not args.limit or len(rows) < args.limit:  # paged: PostgREST caps a response at 1,000 rows
        page = min(1000, args.limit - len(rows)) if args.limit else 1000
        batch = (
            get_supabase()
            .table("games")
            .select("id, user_id, chess_com_username, game_analyses(style_vector)")
            .eq("analysis_status", "complete")
            .order("played_at", desc=True)
            .order("id")
            .range(len(rows), len(rows) + page - 1)
            .execute()
            .data
            or []
        )
        rows += batch
        if len(batch) < page:
            break
    allowed = None
    if args.snapshot:
        payload = json.loads(args.snapshot.read_text(encoding="utf-8"))
        allowed = set(payload["gameIds"] if isinstance(payload, dict) else payload)
    todo = []
    for row in rows:
        if allowed is not None and row["id"] not in allowed:
            continue
        a = row.get("game_analyses")
        vector = (a[0] if isinstance(a, list) and a else a or {}).get("style_vector") or {}
        if args.all or vector.get("version") != VERSION:
            todo.append(row)
    print(f"{len(todo)} of {len(rows)} games need Brilliant rule {VERSION}")
    if args.dry_run:
        return
    service, changed, users = BrilliantFindRate(), 0, set()
    for row in todo:
        result = service.apply(row["id"]) or {}
        changed += result.get("changed", 0)
        users.add((row.get("user_id"), row.get("chess_com_username")))
        if result.get("changed"):
            print(f"  {row['id']}: {result['changed']} moves changed, Brilliant {result.get('brilliantPct')}%", flush=True)
    for user_id, username in users:
        asyncio.run(BaselineService().recompute_baseline(user_id=user_id, chess_com_username=username))
    print(f"Done: {changed} moves changed across {len(todo)} games")


if __name__ == "__main__":
    main()
