import io
from dataclasses import dataclass
from typing import Literal

import chess
import chess.pgn

from app.db.supabase import get_supabase
from app.services.pgn_parser import parse_chess_com_game

ImportOutcome = Literal["new", "skipped", "updated", "invalid"]


@dataclass
class ImportBatchResult:
    new: int = 0
    skipped: int = 0
    updated: int = 0
    invalid: int = 0

    @property
    def stored(self) -> int:
        return self.new + self.updated

    def record(self, outcome: ImportOutcome) -> None:
        if outcome == "invalid":
            self.invalid += 1
        else:
            setattr(self, outcome, getattr(self, outcome) + 1)


class GameStore:
    async def upsert_imported_game(
        self,
        raw: dict,
        username: str,
        user_id: str | None = None,
    ) -> ImportOutcome:
        parsed = parse_chess_com_game(raw, username)
        if parsed is None:
            return "invalid"

        sb = get_supabase()
        existing = (
            sb.table("games")
            .select("id, analysis_status, chess_com_username, user_id")
            .eq("external_id", parsed["external_id"])
            .limit(1)
            .execute()
        )
        existing_rows = existing.data or []
        if existing_rows:
            existing_row = existing_rows[0]
            same_owner = existing_row.get("user_id") == user_id
            same_username = (
                existing_row.get("chess_com_username") == username
            )
            if same_owner and same_username:
                return "skipped"

            analysis_status = existing_row.get("analysis_status") or "pending"
            sb.table("games").upsert(
                {
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
                },
                on_conflict="external_id",
            ).execute()
            return "updated"

        sb.table("games").upsert(
            {
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
                "analysis_status": "pending",
            },
            on_conflict="external_id",
        ).execute()
        return "new"

    async def store_imported_games(
        self,
        username: str,
        games: list[dict],
        user_id: str | None = None,
    ) -> ImportBatchResult:
        totals = ImportBatchResult()
        for raw in games:
            outcome = await self.upsert_imported_game(raw, username, user_id)
            totals.record(outcome)
        return totals

    @staticmethod
    def pgn_to_moves(pgn_text: str) -> list[str]:
        game = chess.pgn.read_game(io.StringIO(pgn_text))
        if game is None:
            return []
        return [move.uci() for move in game.mainline_moves()]

    @staticmethod
    def count_moves(pgn_text: str) -> int:
        return len(GameStore.pgn_to_moves(pgn_text))
