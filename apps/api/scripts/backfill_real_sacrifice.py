"""
Add the `real_sacrifice` signal (review F2) to moves analysed before it existed. Board-only: no engine.

Usage:
    cd apps/api
    python -m scripts.backfill_real_sacrifice

Only moves already tagged with the loose `sacrifice` signal can qualify, so those are the only ones replayed and
checked with `real_offer`. Re-runnable: moves that already carry `real_sacrifice` are left alone.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Allow running as script from apps/api
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db.supabase import get_supabase
from app.services.brilliant import MIN_BRILLIANT_SACRIFICE_VALUE, real_offer
from app.services.library import boards_before

PAGE = 1000


def main() -> None:
    sb = get_supabase()
    tagged: list[dict] = []
    while True:
        batch = (
            sb.table("game_moves").select("id, game_id, ply, signals").filter("signals", "cs", '["sacrifice"]')
            .order("id").range(len(tagged), len(tagged) + PAGE - 1).execute().data
            or []
        )
        tagged += batch
        if len(batch) < PAGE:
            break
    by_game: dict[str, list[dict]] = {}
    for m in tagged:
        if "real_sacrifice" not in (m.get("signals") or []):
            by_game.setdefault(m["game_id"], []).append(m)
    added = 0
    for n, (game_id, moves) in enumerate(by_game.items(), 1):
        game = sb.table("games").select("pgn").eq("id", game_id).limit(1).execute().data
        if not game:
            continue
        plies = boards_before(game[0].get("pgn") or "")
        for m in moves:
            if m["ply"] < len(plies) and real_offer(*plies[m["ply"]]) >= MIN_BRILLIANT_SACRIFICE_VALUE:
                sb.table("game_moves").update({"signals": [*m["signals"], "real_sacrifice"]}).eq("id", m["id"]).execute()
                added += 1
        if n % 200 == 0:
            print(f"{n}/{len(by_game)} games checked, {added} real sacrifices", flush=True)
    print(f"Done: {len(tagged)} loosely tagged moves checked, {added} marked real_sacrifice.")


if __name__ == "__main__":
    main()
