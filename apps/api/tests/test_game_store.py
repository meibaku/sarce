from unittest.mock import AsyncMock, patch

import pytest

from app.services.game_store import GameStore, ImportBatchResult


class TestGameStoreImportOutcomes:
    @pytest.mark.asyncio
    @patch("app.services.game_store.get_supabase")
    async def test_skips_existing_game_for_same_user(self, mock_get_supabase):
        class FakeResult:
            def __init__(self, data):
                self.data = data

        class FakeQuery:
            def select(self, *_args):
                return self

            def eq(self, *_args):
                return self

            def limit(self, *_args):
                return self

            def upsert(self, *_args, **_kwargs):
                raise AssertionError("upsert should not run for cached games")

            def execute(self):
                return FakeResult(
                    [
                        {
                            "id": "game-1",
                            "analysis_status": "complete",
                            "chess_com_username": "dratius",
                            "user_id": "user-1",
                        }
                    ]
                )

        mock_get_supabase.return_value.table.return_value = FakeQuery()
        store = GameStore()

        outcome = await store.upsert_imported_game(
            {
                "pgn": "1. e4 e5 *",
                "white": {"username": "dratius", "result": "win"},
                "black": {"username": "bot"},
                "url": "https://chess.com/game/1",
            },
            "dratius",
            "user-1",
        )

        assert outcome == "skipped"

    @pytest.mark.asyncio
    @patch("app.services.game_store.get_supabase")
    async def test_inserts_new_game(self, mock_get_supabase):
        upsert_calls = []

        class FakeResult:
            def __init__(self, data):
                self.data = data

        class FakeQuery:
            def select(self, *_args):
                return self

            def eq(self, *_args):
                return self

            def limit(self, *_args):
                return self

            def upsert(self, row, **_kwargs):
                upsert_calls.append(row)
                return self

            def execute(self):
                if upsert_calls:
                    return FakeResult([upsert_calls[-1]])
                return FakeResult([])

        mock_get_supabase.return_value.table.return_value = FakeQuery()
        store = GameStore()

        outcome = await store.upsert_imported_game(
            {
                "pgn": "1. e4 e5 *",
                "white": {"username": "dratius", "result": "win"},
                "black": {"username": "bot"},
                "url": "https://chess.com/game/2",
            },
            "dratius",
            "user-1",
        )

        assert outcome == "new"
        assert upsert_calls[0]["analysis_status"] == "pending"

    @pytest.mark.asyncio
    @patch("app.services.game_store.get_supabase")
    async def test_store_imported_games_aggregates_counts(self, mock_get_supabase):
        store = GameStore()
        store.upsert_imported_game = AsyncMock(side_effect=["new", "skipped", "invalid"])

        result = await store.store_imported_games(
            "dratius",
            [{"pgn": "1. e4 *"}, {"pgn": "1. d4 *"}, {}],
            "user-1",
        )

        assert result == ImportBatchResult(new=1, skipped=1, invalid=1)
