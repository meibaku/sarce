"""First read fast (app/services/importer.py, plan 3.1): newest games first, older months in the background."""

import asyncio
from unittest.mock import AsyncMock, patch

from app.services import importer as imp
from app.services.sync import first_read_seconds


class FakeChessCom:
    def __init__(self, months: dict[str, list[dict]]):
        self.months, self.fetched = months, []

    async def fetch_games_from_archive(self, url):
        self.fetched.append(url)
        return self.months[url]


def month(tag: str, n: int) -> list[dict]:
    return [{"url": f"{tag}-{i}", "pgn": "1. e4 *"} for i in range(n)]  # oldest first, as Chess.com lists them


def run(coro):
    return asyncio.run(coro)


@patch("app.services.importer.mark_first_import")
def test_newest_month_is_stored_first_and_the_rest_waits(_mark):
    archives = ["2026/08", "2026/09", "2026/10"]  # oldest first
    client = FakeChessCom({"2026/08": month("aug", 30), "2026/09": month("sep", 15), "2026/10": month("oct", 12)})
    store = AsyncMock()
    store.store_imported_games.side_effect = lambda **kw: len(kw["games"])
    first = run(imp.FirstReadImporter(client, None, store).chess_com_first("kestrel", "u1", archives, None))
    stored_games = store.store_imported_games.await_args.kwargs["games"]
    assert first["stored"] == imp.FIRST_READ_GAMES
    assert stored_games[0]["url"] == "oct-11" and stored_games[11]["url"] == "oct-0" and stored_games[12]["url"] == "sep-14"
    assert client.fetched == ["2026/10", "2026/09"]  # August not fetched before answering
    assert first["rest"] == ["2026/09", "2026/08"]  # September was cut short: the backfill finishes it
    assert first["left"] is None and "oct-0" in first["skip"]


@patch("app.services.importer.mark_first_import")
def test_backfill_skips_stored_games_and_queues_analysis(_mark):
    client = FakeChessCom({"2026/09": month("sep", 15), "2026/08": month("aug", 30)})
    store = AsyncMock()
    store.store_imported_games.side_effect = lambda **kw: len(kw["games"])
    analyse = AsyncMock()
    skip = {f"sep-{i}" for i in range(7, 15)}
    with patch.object(imp.settings, "job_queue_enabled", False):
        stored = run(imp.FirstReadImporter(client, None, store).chess_com_backfill("kestrel", "u1", ["2026/09", "2026/08"], None, analyse, skip))
    assert stored == 7 + 30
    analyse.assert_awaited_once_with(user_id="u1", chess_com_username="kestrel", limit=37)


@patch("app.services.importer.mark_first_import")
def test_a_small_cap_needs_no_backfill(_mark):
    client = FakeChessCom({"2026/10": month("oct", 12)})
    store = AsyncMock()
    store.store_imported_games.side_effect = lambda **kw: len(kw["games"])
    first = run(imp.FirstReadImporter(client, None, store).chess_com_first("kestrel", "u1", ["2026/10"], 5))
    assert first["stored"] == 5 and first["rest"] == [] and first["left"] == 0


def test_first_read_seconds():
    assert first_read_seconds({"firstImportAt": "2026-10-24T10:00:00+00:00", "firstReadAt": "2026-10-24T10:03:30+00:00"}) == 210
    assert first_read_seconds({"firstImportAt": "2026-10-24T10:00:00+00:00"}) is None
