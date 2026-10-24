"""
First read fast (implementation plan 3.1): an import stores and queues the newest games first, then backfills.

Chess.com lists monthly archives oldest first and the old import fetched every month before storing anything, so
a long history kept a new player waiting for their first style read. Now the newest archives are fetched until
FIRST_READ_GAMES games are in hand; those are stored and queued for analysis (newest first, as the queue already
works), the request answers, and the older months follow in a background task that queues them when done.
Lichess is asked for the newest FIRST_READ_GAMES first, then for the full count. Finished games only, as before.

The first import and the first completed analysis are recorded on the profile (`firstImportAt`, `firstReadAt`),
so `/users/sync-status` can say how long the first read took.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Awaitable, Callable

from app.config import settings
from app.services.game_store import GameStore
from app.services.lichess import parse_lichess_game

logger = logging.getLogger(__name__)

FIRST_READ_GAMES = 20

Analyse = Callable[..., Awaitable[object]]


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


async def analyse_later(analyse: Analyse, user_id: str | None, username: str | None, limit: int) -> None:
    """Queue analysis from a background task: a durable job when the queue is on, else run it here."""
    if settings.job_queue_enabled:
        from app.services.job_queue import JobQueue

        JobQueue().enqueue("analyze_pending", user_id, username, {"limit": limit})
        return
    await analyse(user_id=user_id, chess_com_username=username, limit=limit)


def mark_first_import(user_id: str | None) -> None:
    """Records the owner's first import once; a failure here must never stop the import."""
    if not user_id:
        return
    try:
        from app.services.settings_store import SettingsStore

        SettingsStore().record_once(user_id, "firstImportAt", now())
    except Exception:
        logger.exception("Could not record the first import for %s", user_id)


class FirstReadImporter:
    def __init__(self, chess_com, lichess, store: GameStore | None = None) -> None:
        self.chess_com, self.lichess = chess_com, lichess
        self.store = store or GameStore()

    async def chess_com_first(
        self, username: str, user_id: str | None, archives: list[str], max_games: int | None
    ) -> dict:
        """
        Stores the newest games (up to FIRST_READ_GAMES, or max_games if smaller). Returns {stored, rest: archives
        still to fetch (newest first), left: how many more games the cap allows (None = no cap), skip: the stored
        games' ids, for the backfill}.
        """
        mark_first_import(user_id)
        first_cap = min(FIRST_READ_GAMES, max_games) if max_games else FIRST_READ_GAMES
        newest_first = list(reversed(archives))
        games: list[dict] = []
        fetched = 0
        for url in newest_first:
            month = await self.chess_com.fetch_games_from_archive(url)
            games += list(reversed(month))  # each month is oldest first: keep the whole list newest first
            fetched += 1
            if len(games) >= first_cap:
                break
        first = games[:first_cap]
        stored = await self.store.store_imported_games(username=username, user_id=user_id, games=first)
        left = None if max_games is None else max(0, max_games - len(first))
        # A month cut short is fetched again by the backfill, which skips the games already stored.
        rest = newest_first[fetched - 1 :] if len(games) > first_cap else newest_first[fetched:]
        skip = {g.get("url") or g.get("uuid") for g in first}
        return {"stored": stored, "rest": [] if left == 0 else rest, "left": left, "skip": skip}

    async def chess_com_backfill(
        self,
        username: str,
        user_id: str | None,
        archives: list[str],
        left: int | None,
        analyse: Analyse | None,
        skip: set | None = None,
    ) -> int:
        """Stores the older months, newest first, then queues them for analysis. Never raises."""
        stored = 0
        try:
            for url in archives:
                month = [g for g in reversed(await self.chess_com.fetch_games_from_archive(url)) if (g.get("url") or g.get("uuid")) not in (skip or set())]
                if left is not None:
                    month = month[: max(0, left - stored)]
                if month:
                    stored += await self.store.store_imported_games(username=username, user_id=user_id, games=month)
                if left is not None and stored >= left:
                    break
        except Exception:
            logger.exception("Chess.com backfill failed for %s", username)
        # Whatever was saved is queued, even when a later month failed to fetch.
        if analyse and stored:
            try:
                await analyse_later(analyse, user_id, username, stored)
            except Exception:
                logger.exception("Could not queue the backfill's analysis for %s", username)
        return stored

    async def lichess_first(self, username: str, user_id: str | None, max_games: int) -> tuple[int, set[str]]:
        """Stores the newest finished Lichess games (up to FIRST_READ_GAMES). Returns (stored, their ids)."""
        mark_first_import(user_id)
        raw = await self.lichess.fetch_games(username, max_games=min(FIRST_READ_GAMES, max_games))
        parsed = [g for r in raw if (g := parse_lichess_game(r, username))]
        stored = await self.store.store_parsed_games(username=username, parsed_games=parsed, source="lichess", user_id=user_id)
        return stored, {g["external_id"] for g in parsed}

    async def lichess_backfill(
        self, username: str, user_id: str | None, max_games: int, analyse: Analyse | None, skip: set[str] | None = None
    ) -> int:
        """Fetches the full count and stores the games the first pass didn't, then queues them. Never raises."""
        try:
            raw = await self.lichess.fetch_games(username, max_games=max_games)
            # Skip by id, not by count: variants the parser drops would otherwise shift which games are skipped.
            parsed = [g for r in raw if (g := parse_lichess_game(r, username)) and g["external_id"] not in (skip or set())]
            stored = await self.store.store_parsed_games(username=username, parsed_games=parsed, source="lichess", user_id=user_id) if parsed else 0
            if analyse and stored:
                await analyse_later(analyse, user_id, username, stored)
            return stored
        except Exception:
            logger.exception("Lichess backfill failed for %s", username)
            return 0
