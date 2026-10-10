"""
Intention tagger — Chaos Lens M7 (docs/CHAOS_PLAN.md).

Turns a finished game into motif tags per ply (`move_tags`) and idea windows with a
verdict (`game_ideas`). Engine-free: it reads the PGN and stored Phase 1 evals only.
"""

from __future__ import annotations

import io

import chess
import chess.pgn

from app.db.supabase import get_supabase
from app.services.ideas import build_ply_states, find_ideas
from app.services.motifs import move_motifs


def tag_game_data(pgn_text: str, user_color: str, move_rows: list[dict]) -> dict:
    """Pure: motif tags for every ply and the user's idea windows."""
    game = chess.pgn.read_game(io.StringIO(pgn_text))
    if game is None:
        return {"tags": [], "ideas": []}
    board, moves = game.board(), list(game.mainline_moves())
    user = chess.WHITE if user_color == "white" else chess.BLACK

    tags, temp = [], board.copy()
    for ply, move in enumerate(moves):
        by_user = temp.turn == user
        for tag in move_motifs(temp, move):
            tags.append({"ply": ply, "by_user": by_user, "tag": tag})
        temp.push(move)

    evals = {row["ply"]: row.get("eval_after") for row in move_rows}
    ideas = find_ideas(build_ply_states(board, moves, user_color, evals))
    return {"tags": tags, "ideas": ideas}


class TaggerService:
    """Supabase-backed tagging and reading of motif tags and idea windows."""

    def tag_game(self, game_id: str) -> dict | None:
        """(Re)tag one game. Returns the tags and ideas, or None if the game is unknown."""
        sb = get_supabase()
        game = sb.table("games").select("id, pgn, user_color").eq("id", game_id).limit(1).execute()
        if not game.data:
            return None
        row = game.data[0]
        moves = (
            sb.table("game_moves").select("ply, eval_after").eq("game_id", game_id).execute()
        ).data or []
        result = tag_game_data(row["pgn"], row.get("user_color") or "white", moves)

        sb.table("move_tags").delete().eq("game_id", game_id).execute()
        sb.table("game_ideas").delete().eq("game_id", game_id).execute()
        if result["tags"]:
            sb.table("move_tags").insert(
                [{"game_id": game_id, **tag} for tag in result["tags"]]
            ).execute()
        if result["ideas"]:
            sb.table("game_ideas").insert(
                [{"game_id": game_id, **idea} for idea in result["ideas"]]
            ).execute()
        return result

    def get_game_ideas(self, game_id: str) -> dict:
        """Stored tags and ideas for a game, shaped for the review UI."""
        sb = get_supabase()
        tags = (
            sb.table("move_tags").select("ply, by_user, tag").eq("game_id", game_id).order("ply").execute()
        ).data or []
        ideas = (
            sb.table("game_ideas")
            .select("family, start_ply, end_ply, verdict, is_pivot")
            .eq("game_id", game_id)
            .order("start_ply")
            .execute()
        ).data or []
        return {
            "gameId": game_id,
            "tags": [{"ply": t["ply"], "byUser": t["by_user"], "tag": t["tag"]} for t in tags],
            "ideas": [
                {
                    "family": i["family"],
                    "startPly": i["start_ply"],
                    "endPly": i["end_ply"],
                    "verdict": i["verdict"],
                    "isPivot": i["is_pivot"],
                }
                for i in ideas
            ],
        }
