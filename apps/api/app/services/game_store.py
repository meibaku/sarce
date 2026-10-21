import io
from datetime import datetime

import chess
import chess.pgn

from app.db.supabase import get_supabase
from app.services.pgn_parser import opening_from_pgn, parse_chess_com_game


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
                **dict(zip(("eco", "opening"), opening_from_pgn(parsed["pgn"]))),
                # No analysis_status here: new rows default to 'pending', and re-importing
                # a game must not reset one that has already been analysed.
            }

            sb.table("games").upsert(row, on_conflict="external_id").execute()
            stored += 1

        return stored

    async def store_parsed_games(
        self,
        username: str,
        parsed_games: list[dict],
        source: str,
        user_id: str | None = None,
    ) -> int:
        """Store already-parsed games from another site (needs the game_source migration)."""
        sb = get_supabase()
        for parsed in parsed_games:
            row = {
                **parsed,
                "user_id": user_id,
                "chess_com_username": username,
                "source": source,
                **dict(zip(("eco", "opening"), opening_from_pgn(parsed.get("pgn")))),
                # analysis_status is left to the column default; see store_imported_games.
            }
            sb.table("games").upsert(row, on_conflict="external_id").execute()
        return len(parsed_games)

    @staticmethod
    def pgn_to_moves(pgn_text: str) -> list[str]:
        game = chess.pgn.read_game(io.StringIO(pgn_text))
        if game is None:
            return []
        return [move.uci() for move in game.mainline_moves()]

    @staticmethod
    def count_moves(pgn_text: str) -> int:
        return len(GameStore.pgn_to_moves(pgn_text))
