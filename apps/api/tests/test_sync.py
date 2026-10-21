"""Automatic sync (app/services/sync.py) and the username settings it reads."""

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from app.config import settings
from app.services import settings_store
from app.services.sync import SyncService


def test_username_validation():
    assert settings_store.validate({"chessComUsername": " dratius "}) == {"chessComUsername": "dratius"}
    assert settings_store.validate({"lichessUsername": None}) == {"lichessUsername": None}
    with pytest.raises(ValueError):
        settings_store.validate({"chessComUsername": "bad name!"})
    with pytest.raises(ValueError):
        settings_store.validate({"lastSyncedAt": "2026-10-18"})  # written by the sync only


def run_sync(prefs, chess_com=0, lichess=0):
    service = SyncService()
    store = type("S", (), {"get": lambda self, o: prefs, "record_sync": lambda self, *a: None})()
    analyse = AsyncMock(return_value=[{"gameId": "g"}])
    with patch("app.services.settings_store.SettingsStore", return_value=store), \
         patch.object(service, "_chess_com", AsyncMock(return_value=chess_com)) as cc, \
         patch.object(service, "_lichess", AsyncMock(return_value=lichess)) as li:
        result = asyncio.run(service.sync("owner", analyse))
    return result, cc, li, analyse


def test_sync_fetches_saved_sources_then_analyses_newest():
    prefs = {"chessComUsername": "dratius", "lichessUsername": "drat", "sources": "both"}
    result, cc, li, analyse = run_sync(prefs, chess_com=3, lichess=2)
    assert result == {"fetched": 5, "analysed": 1, "errors": []}
    cc.assert_awaited_once() and li.assert_awaited_once()
    analyse.assert_awaited_once_with(user_id="owner", limit=max(5, settings.workers))


def test_sync_respects_the_sources_setting():
    result, cc, li, _ = run_sync({"chessComUsername": "dratius", "lichessUsername": "drat", "sources": "lichess"}, lichess=1)
    assert cc.await_count == 0 and li.await_count == 1 and result["fetched"] == 1


def test_one_site_failing_does_not_stop_the_other():
    service = SyncService()
    store = type("S", (), {"get": lambda self, o: {"chessComUsername": "a1", "lichessUsername": "b1", "sources": "both"}, "record_sync": lambda self, *a: None})()
    with patch("app.services.settings_store.SettingsStore", return_value=store), \
         patch.object(service, "_chess_com", AsyncMock(side_effect=RuntimeError("down"))), \
         patch.object(service, "_lichess", AsyncMock(return_value=2)):
        result = asyncio.run(service.sync("owner", AsyncMock(return_value=[])))
    assert result["fetched"] == 2 and result["errors"] == ["Chess.com: down"]


def test_sync_loop_keeps_going_while_games_are_pending(monkeypatch):
    from app.services import sync as sync_module

    sleeps = []

    class Service:
        calls = 0

        async def sync(self, owner, analyse):
            Service.calls += 1
            return {"analysed": 5 if Service.calls == 1 else 0}

    async def fake_sleep(seconds):
        sleeps.append(seconds)
        if len(sleeps) == 2:
            raise asyncio.CancelledError

    monkeypatch.setattr(sync_module.asyncio, "sleep", fake_sleep)
    with pytest.raises(asyncio.CancelledError):
        asyncio.run(sync_module.sync_loop(Service(), "me", None, minutes=5))
    assert sleeps == [sync_module.BACKLOG_PAUSE_S, 300]
