"""
Re-score every analysed game with the current lens registry, from stored data only.

Usage:
    cd apps/api
    python -m scripts.rescore_lenses [--limit 0] [--only-missing squeeze]

Lenses are pure functions over `position_evals` and `human_probs` (docs/CHAOS_PLAN.md, rule 3), so a new lens
such as squeeze reaches past games without Stockfish or a human model. `--only-missing NAME` skips games that
already have rows for that lens, so the script can be re-run after an interruption.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Allow running as script from apps/api
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db.supabase import get_supabase
from app.services.lens_service import LensService

PAGE = 1000


def game_ids(only_missing: str | None, snapshot: Path | None = None) -> list[str]:
    sb = get_supabase()
    ids: list[str] = []
    while True:
        batch = sb.table("games").select("id").eq("analysis_status", "complete").order("played_at", desc=True).range(len(ids), len(ids) + PAGE - 1).execute().data or []
        ids += [r["id"] for r in batch]
        if len(batch) < PAGE:
            break
    if only_missing:
        done: set[str] = set()
        rows: list[dict] = []
        while True:
            batch = sb.table("move_lens_scores").select("game_id").eq("lens", only_missing).range(len(rows), len(rows) + PAGE - 1).execute().data or []
            rows += batch
            if len(batch) < PAGE:
                break
        done = {r["game_id"] for r in rows}
        ids = [i for i in ids if i not in done]
    if snapshot:
        payload = json.loads(snapshot.read_text(encoding="utf-8"))
        allowed = set(payload["gameIds"] if isinstance(payload, dict) else payload)
        ids = [game_id for game_id in ids if game_id in allowed]
    return ids


def main(limit: int, only_missing: str | None, snapshot: Path | None = None) -> None:
    ids = game_ids(only_missing, snapshot)
    if limit:
        ids = ids[:limit]
    service = LensService()
    failed = 0
    for n, gid in enumerate(ids, 1):
        try:
            service.score_game(gid)
        except Exception as exc:  # one bad game must not stop the run
            failed += 1
            print(f"  {gid}: {exc}")
        if n % 50 == 0:
            print(f"{n}/{len(ids)} games re-scored", flush=True)
    print(f"Done: {len(ids) - failed} games re-scored, {failed} failed.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Re-score analysed games with the current lenses")
    parser.add_argument("--limit", type=int, default=0, help="Games per run (0 = all)")
    parser.add_argument("--only-missing", default=None, help="Skip games that already have rows for this lens")
    parser.add_argument("--snapshot", type=Path, help="Only game IDs in this fixed manifest")
    args = parser.parse_args()
    main(args.limit, args.only_missing, args.snapshot)
