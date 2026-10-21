"""
Saved positions (Review → "Add to Train", PHASES 2.1). A saved position is a FEN the player wants to
see again; Train drills it as "a saved position". When it comes from a game, the engine's move at
that point (game_moves.best_san) is stored as the answer, so the drill can say whether you found it.
"""

from __future__ import annotations

import chess

from app.db.supabase import get_supabase

TITLE_MAX, NOTE_MAX, EXCERPT_MAX = 80, 2000, 6000


def clean_fen(fen: str) -> str:
    """The FEN of a legal position, normalised; raises ValueError otherwise."""
    board = chess.Board(fen)
    if not board.is_valid() or board.is_game_over():
        raise ValueError("not a playable position")
    return board.fen()


class PositionStore:
    def save(
        self,
        owner_id: str,
        fen: str,
        title: str | None,
        note: str | None,
        game_id: str | None,
        ply: int | None,
        source: dict | None = None,
    ) -> dict:
        """`source`: {url, time_s, excerpt, ai_summary} for a position taken from a video."""
        fen = clean_fen(fen)
        best = None
        if game_id is not None and ply is not None:
            rows = get_supabase().table("game_moves").select("best_san").eq("game_id", game_id).eq("ply", ply).limit(1).execute().data or []
            best = rows[0].get("best_san") if rows else None
        row = {
            "user_id": owner_id,
            "fen": fen,
            "title": (title or "Saved position").strip()[:TITLE_MAX] or "Saved position",
            "note": (note or "").strip()[:NOTE_MAX],
            "best_san": best,
            "game_id": game_id,
            "ply": ply,
        }
        if source:
            row.update({
                "source_url": (source.get("url") or None),
                "source_time_s": source.get("time_s"),
                "excerpt": (source.get("excerpt") or "")[:EXCERPT_MAX],
                "ai_summary": (source.get("ai_summary") or "")[:NOTE_MAX],
            })
        return get_supabase().table("saved_positions").upsert(row, on_conflict="user_id,fen").execute().data[0]

    def list(self, owner_id: str, limit: int = 50, q: str | None = None) -> list[dict]:
        rows = (
            get_supabase().table("saved_positions").select("*").eq("user_id", owner_id).order("created_at", desc=True).limit(500 if q else limit).execute().data
            or []
        )
        return search(rows, q)[:limit] if q else rows

    def delete(self, owner_id: str, position_id: str) -> None:
        get_supabase().table("saved_positions").delete().eq("user_id", owner_id).eq("id", position_id).execute()


def search(rows: list[dict], q: str) -> list[dict]:
    """Saved positions whose title, note, transcript excerpt or summary contain every word of `q`."""
    words = [w for w in q.lower().split() if w]

    def text(r: dict) -> str:
        return " ".join(str(r.get(k) or "") for k in ("title", "note", "excerpt", "ai_summary", "best_san")).lower()

    return [r for r in rows if all(w in text(r) for w in words)]


def drill_items(rows: list[dict]) -> list[dict]:
    """Train items for saved positions (source "a saved position")."""
    return [
        {
            "key": f"saved:{r['id']}",
            "source": "a saved position",
            "meta": "from a video" if r.get("source_url") else "you saved it",
            "title": r.get("title") or "Saved position",
            "detail": r.get("note") or r.get("ai_summary") or ("Find the move you were looking for." if r.get("best_san") else "Play the move you'd choose; Sarce says whether it holds."),
            "fen": r["fen"],
            "answer": r.get("best_san"),
            "gameId": r.get("game_id"),
            "ply": r.get("ply"),
        }
        for r in rows
    ]
