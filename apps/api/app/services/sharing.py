"""
Shared links (M8): a read-only page for one game summary or one sacrifice, made by its owner.

The snapshot is built when the link is made and stored with it, so the public page never reads live data:
later notes, re-analysis or other games can't leak through a link. Snapshots name no third party (the
opponent becomes "an opponent") and leave out the owner's private notes. Tokens are 128-bit random.
"""

from __future__ import annotations

import secrets
from datetime import datetime, timezone

from app.db.supabase import get_supabase

KINDS = ("summary", "sacrifice")


def new_token() -> str:
    return secrets.token_urlsafe(16)


def summary_snapshot(summary: dict) -> dict:
    """The public part of a game summary: what happened in style terms, no names, no notes."""
    from app.services.summary import move_label

    return {
        "kind": "summary",
        "result": summary.get("result"),
        "userColor": summary.get("userColor"),
        "timeControl": summary.get("timeControl"),
        "headline": summary.get("headline"),
        "outcome": (summary.get("outcome") or {}).get("text"),
        "brilliant": {k: (summary.get("brilliant") or {}).get(k) for k in ("pct", "count", "of", "goalLo", "goalHi")},
        "moments": [{"label": move_label(m["ply"], m.get("san")), "glyph": m.get("glyph"), "line": m.get("line")} for m in summary.get("moments", [])],
        "styleRead": summary.get("styleRead"),
    }


def sacrifice_snapshot(row: dict, fen: str) -> dict:
    """A sacrifice as a puzzle-like card: the position before it, the move, what it gave and whether it held."""
    return {
        "kind": "sacrifice",
        "fen": fen,
        "label": row["label"],
        "glyph": row["glyph"],
        "type": row["type"],
        "material": row["material"],
        "held": row["held"],
        "opening": row.get("opening"),
        "playedAt": (row.get("playedAt") or "")[:10] or None,
    }


class ShareService:
    def create(self, owner_id: str, kind: str, game_id: str, ply: int | None) -> dict:
        """Makes a link for the owner's own game; raises LookupError when the game isn't theirs."""
        from app.services.library import LibraryService, boards_before
        from app.services.summary import SummaryService

        if kind not in KINDS:
            raise ValueError(f"kind must be one of {KINDS}")
        sb = get_supabase()
        games = sb.table("games").select("id, user_id, pgn").eq("id", game_id).limit(1).execute().data or []
        if not games or games[0].get("user_id") != owner_id:
            raise LookupError("game not found")
        if kind == "summary":
            summary = SummaryService().summary(game_id, owner_id, owner_id)
            if summary is None:
                raise LookupError("game not found")
            snapshot = summary_snapshot(summary)
        else:
            if ply is None:
                raise ValueError("a sacrifice link needs the move (ply)")
            row = next((r for r in LibraryService().sacrifices(owner_id, None, limit=10_000) if r["gameId"] == game_id and r["ply"] == ply), None)
            if row is None:
                raise LookupError("sacrifice not found")
            boards = boards_before(games[0].get("pgn") or "")
            snapshot = sacrifice_snapshot(row, boards[ply][0].fen())
        rec = {"token": new_token(), "user_id": owner_id, "kind": kind, "game_id": game_id, "ply": ply, "snapshot": snapshot}
        return sb.table("shared_links").insert(rec).execute().data[0]

    def mine(self, owner_id: str) -> list[dict]:
        return (
            get_supabase().table("shared_links").select("id, token, kind, game_id, ply, created_at, revoked_at, snapshot")
            .eq("user_id", owner_id).order("created_at", desc=True).limit(100).execute().data
            or []
        )

    def revoke(self, owner_id: str, link_id: str) -> None:
        get_supabase().table("shared_links").update({"revoked_at": datetime.now(timezone.utc).isoformat()}).eq("user_id", owner_id).eq("id", link_id).execute()

    def public(self, token: str) -> dict | None:
        """The snapshot for a live token, or None (unknown or revoked)."""
        rows = get_supabase().table("shared_links").select("kind, snapshot, created_at, revoked_at").eq("token", token).limit(1).execute().data or []
        if not rows or rows[0].get("revoked_at"):
            return None
        return {**rows[0]["snapshot"], "sharedAt": rows[0]["created_at"]}
