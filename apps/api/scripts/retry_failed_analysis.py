"""Preview or explicitly requeue failed game analyses while clearing their retry budget."""

from __future__ import annotations

import argparse

from app.db.supabase import get_supabase


def candidates(game_id: str | None) -> list[dict]:
    query = get_supabase().table("games").select("id, played_at, analysis_attempts, analysis_error").eq(
        "analysis_status", "failed"
    )
    if game_id:
        query = query.eq("id", game_id)
    return query.order("played_at").execute().data or []


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--game-id")
    group.add_argument("--all", action="store_true")
    parser.add_argument("--apply", action="store_true", help="Requeue matches; omission is a dry run")
    args = parser.parse_args()

    rows = candidates(args.game_id)
    for row in rows:
        print(f"{row['id']} attempts={row.get('analysis_attempts', 0)} error={row.get('analysis_error') or '-'}")
    if args.apply and rows:
        ids = [row["id"] for row in rows]
        get_supabase().table("games").update({
            "analysis_status": "pending",
            "analysis_attempts": 0,
            "analysis_error": None,
            "analysis_failed_at": None,
        }).in_("id", ids).eq("analysis_status", "failed").execute()
        print(f"requeued={len(ids)}")
    else:
        print(f"dry_run={len(rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
