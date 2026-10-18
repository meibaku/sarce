"""
Automatic game sync: new finished games arrive by themselves and are analysed in the background.

Every SYNC_MINUTES (when AUTO_SYNC_ENABLED is on) the API fetches the newest finished games for the
usernames saved in Settings, stores them, and analyses up to ANALYSE_PER_SYNC pending games, newest
first, with the Chaos Lens pass when POSITION_EVALS_ENABLED is on. Chess.com's monthly archives hold
finished games only and Lichess is asked for finished games only, so nothing here can touch a game
in progress (post-game only). Requests are serial, as both sites ask.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

from app.config import settings
from app.db.supabase import get_supabase
from app.services.chess_com import ChessComClient, normalize_chess_com_username
from app.services.game_store import GameStore
from app.services.lichess import LichessClient, normalize_lichess_username, parse_lichess_game

logger = logging.getLogger(__name__)

ANALYSE_PER_SYNC = 5
LICHESS_PER_SYNC = 20


class SyncService:
    def __init__(self) -> None:
        self.store = GameStore()
        self._lock = asyncio.Lock()

    async def sync(self, owner_id: str, analyse) -> dict:
        """
        Fetches new games for the owner's saved usernames, then analyses pending games.
        `analyse(user_id, limit)` is the analysis entry point (AnalysisService.analyze_pending).
        """
        from app.services.settings_store import SettingsStore

        if self._lock.locked():
            return {"skipped": "a sync is already running"}
        async with self._lock:
            store = SettingsStore()
            prefs = store.get(owner_id)
            imported, errors = 0, []
            if prefs.get("chessComUsername") and prefs["sources"] in ("chess_com", "both"):
                try:
                    imported += await self._chess_com(prefs["chessComUsername"], owner_id)
                except Exception as exc:  # one site failing must not stop the other
                    errors.append(f"Chess.com: {exc}")
            if prefs.get("lichessUsername") and prefs["sources"] in ("lichess", "both"):
                try:
                    imported += await self._lichess(prefs["lichessUsername"], owner_id)
                except Exception as exc:
                    errors.append(f"Lichess: {exc}")
            store.record_sync(owner_id, datetime.now(timezone.utc).isoformat(), errors)
            # At least one game per analysis worker, so a sync keeps every engine busy.
            analysed = await analyse(user_id=owner_id, limit=max(ANALYSE_PER_SYNC, settings.workers))
            return {"fetched": imported, "analysed": len(analysed or []), "errors": errors}

    async def _chess_com(self, username: str, owner_id: str) -> int:
        client = ChessComClient()
        name = normalize_chess_com_username(username)
        archives = await client.fetch_recent_archives(name, limit=1)
        games = []
        for url in archives:
            games.extend(await client.fetch_games_from_archive(url))
        return await self.store.store_imported_games(username=name, user_id=owner_id, games=games)

    async def _lichess(self, username: str, owner_id: str) -> int:
        name = normalize_lichess_username(username)
        raw = await LichessClient().fetch_games(name, max_games=LICHESS_PER_SYNC)
        parsed = [g for r in raw if (g := parse_lichess_game(r, name))]
        return await self.store.store_parsed_games(username=name, parsed_games=parsed, source="lichess", user_id=owner_id)

    def status(self, owner_id: str, user_id: str | None) -> dict:
        from app.services.settings_store import SettingsStore

        prefs = SettingsStore().get(owner_id)
        sb = get_supabase()

        def count(status: str) -> int:
            q = sb.table("games").select("id", count="exact").eq("analysis_status", status).limit(1)
            if user_id:
                q = q.eq("user_id", user_id)
            return q.execute().count or 0

        return {
            "chessComUsername": prefs.get("chessComUsername"),
            "lichessUsername": prefs.get("lichessUsername"),
            "sources": prefs.get("sources"),
            "lastSyncedAt": prefs.get("lastSyncedAt"),
            "lastSyncErrors": prefs.get("lastSyncErrors") or [],
            "pending": count("pending"),
            "processing": count("processing"),
            "autoSync": settings.auto_sync_enabled,
            "chaosPass": settings.position_evals_enabled,
        }


async def sync_loop(service: SyncService, owner_id: str, analyse, minutes: float) -> None:
    """Background loop started with the API when AUTO_SYNC_ENABLED is on."""
    while True:
        try:
            result = await service.sync(owner_id, analyse)
            logger.info("Sync: %s", result)
        except Exception:
            logger.exception("Sync failed")
        await asyncio.sleep(minutes * 60)
