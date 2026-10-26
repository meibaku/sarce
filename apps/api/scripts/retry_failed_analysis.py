"""Preview or explicitly requeue failed game analyses while clearing their retry budget."""

from __future__ import annotations

import argparse

from app.db.supabase import get_supabase

PAGE_SIZE = 500


def candidates(game_id: str | None) -> list[dict]:
    """Fetch every matching failure in a stable order despite PostgREST row caps."""
    rows: list[dict] = []
    while True:
        query = get_supabase().table("games").select(
            "id, played_at, analysis_attempts, analysis_error, analysis_failed_at"
        ).eq("analysis_status", "failed")
        if game_id:
            query = query.eq("id", game_id)
        batch = (
            query.order("played_at").order("id")
            .range(len(rows), len(rows) + PAGE_SIZE - 1).execute().data or []
        )
        rows.extend(batch)
        if len(batch) < PAGE_SIZE:
            return rows


def requeue(rows: list[dict]) -> int:
    """Clear only the exact failures observed by the dry-run selection."""
    changed = 0
    for row in rows:
        query = get_supabase().table("games").update({
            "analysis_status": "pending",
            "analysis_attempts": 0,
            "analysis_error": None,
            "analysis_failed_at": None,
        }).eq("id", row["id"]).eq("analysis_status", "failed")
        failed_at = row.get("analysis_failed_at")
        query = query.is_("analysis_failed_at", "null") if failed_at is None else query.eq("analysis_failed_at", failed_at)
        changed += len(query.execute().data or [])
    return changed


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
        changed = requeue(rows)
        print(f"requeued={changed} skipped_changed_since_preview={len(rows) - changed}")
    else:
        print(f"dry_run={len(rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
