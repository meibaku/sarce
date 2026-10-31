"""Participant-facing style read built only from admitted Brilliant evidence."""

from app.db.supabase import get_supabase
from app.services.home import format_time_control
from app.services.summary import move_label


class PilotReadService:
    """Build the narrow pilot DTO without exposing normal-product lens payloads."""

    def __init__(self, supabase=None) -> None:
        self.sb = supabase or get_supabase()

    def read(self, user_id: str, game_id: str) -> dict | None:
        rows = (
            self.sb.table("games")
            .select("id, played_at, opponent, result, user_color, time_control, game_analyses(brilliant_pct, total_moves)")
            .eq("id", game_id)
            .eq("user_id", user_id)
            .limit(1)
            .execute()
            .data
            or []
        )
        if not rows:
            return None
        game = rows[0]
        analysis = game.pop("game_analyses", None)
        analysis = analysis[0] if isinstance(analysis, list) and analysis else (analysis or {})
        moves = (
            self.sb.table("game_moves")
            .select("ply, san, is_brilliant, signals")
            .eq("game_id", game_id)
            .eq("is_brilliant", True)
            .order("ply")
            .execute()
            .data
            or []
        )
        moments = [self._moment(move) for move in moves]
        total = int(analysis.get("total_moves") or 0)
        pct = float(analysis.get("brilliant_pct") or 0)
        if moments:
            first = moments[0]
            headline = "You offered material by choice, and it held."
            summary = f"Across {total} moves, {first['label']} is the clearest example: a material offer that stayed inside the Brilliant soundness boundary."
        else:
            headline = "No Brilliant moment appeared in this finished game."
            summary = f"Across {total} moves, Sarce found no move that met all four Brilliant criteria. That is a neutral read, not a grade."
        feedback = (
            self.sb.table("pilot_read_feedback")
            .select("id, game_id, resonance, comment, updated_at")
            .eq("user_id", user_id)
            .eq("game_id", game_id)
            .limit(1)
            .execute()
            .data
            or []
        )
        return {
            "gameId": game_id,
            "playedAt": game.get("played_at"),
            "opponent": game.get("opponent"),
            "result": game.get("result"),
            "userColor": game.get("user_color"),
            "timeControl": format_time_control(game.get("time_control")),
            "moves": total,
            "headline": headline,
            "summary": summary,
            "brilliant": {"pct": round(pct, 1), "count": len(moments), "of": total},
            "moments": moments,
            "feedback": self._feedback(feedback[0]) if feedback else None,
        }

    @staticmethod
    def _moment(move: dict) -> dict:
        label = move_label(move["ply"], move.get("san"))
        return {
            "ply": move["ply"],
            "san": move.get("san"),
            "label": label,
            "line": "Material was offered, and the position stayed sound.",
            "criteria": [
                {"rule": "Material offered", "detail": "The move made a genuine material offer."},
                {"rule": "Sound", "detail": "The move stayed inside Sarce's Brilliant soundness boundary."},
                {"rule": "Not already winning", "detail": "The position was not already decided before the move."},
                {"rule": "Not forced", "detail": "Another move also held, so this was a real choice."},
            ],
        }

    @staticmethod
    def _feedback(row: dict) -> dict:
        return {
            "id": row["id"],
            "gameId": row["game_id"],
            "resonance": row["resonance"],
            "comment": row.get("comment"),
            "savedAt": row["updated_at"],
        }
