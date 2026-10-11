"""Re-importing a game must not reset its analysis status."""

import asyncio
from unittest.mock import MagicMock, patch

from app.services.game_store import GameStore

RAW = {
    "url": "https://chess.com/game/1",
    "end_time": 1710000000,
    "time_control": "60",
    "pgn": '[Event "Live Chess"]\n1. e4 e5 *',
    "white": {"username": "tal_fan", "rating": 1500, "result": "win"},
    "black": {"username": "opponent1", "rating": 1480, "result": "checkmated"},
}


def upserted_rows(sb: MagicMock) -> list[dict]:
    return [call.args[0] for call in sb.table.return_value.upsert.call_args_list]


class TestImportKeepsStatus:
    def test_chess_com_import_does_not_write_analysis_status(self):
        sb = MagicMock()
        with patch("app.services.game_store.get_supabase", return_value=sb):
            stored = asyncio.run(GameStore().store_imported_games("tal_fan", [RAW], user_id="u1"))
        (row,) = upserted_rows(sb)
        assert stored == 1 and row["external_id"] == "https://chess.com/game/1"
        assert "analysis_status" not in row

    def test_parsed_import_does_not_write_analysis_status(self):
        sb = MagicMock()
        parsed = {"external_id": "https://lichess.org/abc", "pgn": "1. e4 *", "user_color": "white"}
        with patch("app.services.game_store.get_supabase", return_value=sb):
            asyncio.run(GameStore().store_parsed_games("tal_fan", [parsed], source="lichess"))
        (row,) = upserted_rows(sb)
        assert row["source"] == "lichess" and "analysis_status" not in row
