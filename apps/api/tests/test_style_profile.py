from unittest.mock import patch

import pytest

from app.services.style_profile import StyleProfileService


class FakeResult:
    def __init__(self, data):
        self.data = data


class FakeQuery:
    def __init__(self, table_name: str, calls: list[tuple[str, str, object]]):
        self.table_name = table_name
        self.calls = calls

    def select(self, *_args):
        return self

    def eq(self, column, value):
        self.calls.append((self.table_name, column, value))
        return self

    def in_(self, column, value):
        self.calls.append((self.table_name, column, value))
        return self

    def execute(self):
        if self.table_name == "games":
            return FakeResult(
                [
                    {
                        "id": "game-1",
                        "pgn": None,
                        "result": "win",
                        "time_control": "600",
                        "opponent_rating": 1800,
                    }
                ]
            )
        return FakeResult([])


class FakeSupabase:
    def __init__(self):
        self.calls = []

    def table(self, table_name):
        return FakeQuery(table_name, self.calls)


@pytest.mark.asyncio
@patch("app.services.style_profile.get_supabase")
async def test_style_profile_handles_null_pgn(mock_get_supabase):
    fake = FakeSupabase()
    mock_get_supabase.return_value = fake

    profile = await StyleProfileService().get_profile(
        chess_com_username="dratius",
    )

    assert profile["gamesAnalyzed"] == 1
    assert profile["favoriteOpening"]["name"] == "Unknown opening"
    assert ("games", "chess_com_username", "dratius") in fake.calls
