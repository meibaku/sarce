import io
from datetime import datetime

import chess
import chess.pgn

from app.db.supabase import get_supabase
from app.services.pgn_parser import parse_chess_com_game


class GameStore:
    async def store_imported_games(
        self,
        username: str,
        games: list[dict],
        user_id: str | None = None,
    ) -> int:
        sb = get_supabase()
        stored = 0

        for raw in games:
            parsed = parse_chess_com_game(raw, username)
            if parsed is None:
                continue

            existing = (
                sb.table("games")
                .select("analysis_status")
                .eq("external_id", parsed["external_id"])
                .maybe_single()
                .execute()
            )
            analysis_status = (
                existing.data.get("analysis_status")
                if existing and existing.data
                else "pending"
            )

            row = {
                "user_id": user_id,
                "chess_com_username": username,
                "external_id": parsed["external_id"],
                "pgn": parsed["pgn"],
                "played_at": parsed["played_at"],
                "opponent": parsed["opponent"],
                "opponent_rating": parsed["opponent_rating"],
                "time_control": parsed["time_control"],
                "result": parsed["result"],
                "user_color": parsed["user_color"],
                "analysis_status": analysis_status,
            }

            sb.table("games").upsert(row, on_conflict="external_id").execute()
            stored += 1

        return stored

    @staticmethod
    def pgn_to_moves(pgn_text: str) -> list[str]:
        game = chess.pgn.read_game(io.StringIO(pgn_text))
        if game is None:
            return []
        return [move.uci() for move in game.mainline_moves()]

    @staticmethod
    def count_moves(pgn_text: str) -> int:
        return len(GameStore.pgn_to_moves(pgn_text))
