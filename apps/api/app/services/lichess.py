"""
Lichess game import — Chaos Lens M8 (docs/CHAOS_PLAN.md).

Uses the public games export (no key needed). Finished standard games only: nothing
here may ever touch a game in progress (rule 6, Lichess fair-play rules).
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

import httpx

from app.config import settings

UNFINISHED_STATUSES = {"created", "started"}


def normalize_lichess_username(username: str) -> str:
    """Lichess usernames are case-insensitive; ids are lowercase."""
    return username.strip().lower()


def parse_ndjson(text: str) -> list[dict]:
    """One JSON object per non-empty line; malformed lines are skipped."""
    games = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            games.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return games


def _player_name(player: dict) -> str:
    return ((player.get("user") or {}).get("name") or "").lower()


def parse_lichess_game(raw: dict, username: str) -> dict | None:
    """
    Map one exported Lichess game to the shape `GameStore` stores.

    Returns None for unfinished games, variants, games without a PGN, or games the
    user did not play in.
    """
    if raw.get("status") in UNFINISHED_STATUSES or raw.get("variant", "standard") != "standard":
        return None
    pgn, game_id = raw.get("pgn"), raw.get("id")
    if not pgn or not game_id:
        return None

    players = raw.get("players") or {}
    white, black = players.get("white") or {}, players.get("black") or {}
    wanted = normalize_lichess_username(username)
    if _player_name(white) == wanted:
        user_color, opponent = "white", black
    elif _player_name(black) == wanted:
        user_color, opponent = "black", white
    else:
        return None

    winner = raw.get("winner")
    result = "draw" if winner not in ("white", "black") else ("win" if winner == user_color else "loss")

    clock = raw.get("clock") or {}
    time_control = None
    if clock.get("initial") is not None:
        increment = clock.get("increment") or 0
        time_control = f"{clock['initial']}+{increment}" if increment else str(clock["initial"])

    played_ms = raw.get("lastMoveAt") or raw.get("createdAt")
    played_at = (
        datetime.fromtimestamp(played_ms / 1000, tz=timezone.utc).isoformat() if played_ms else None
    )
    return {
        "external_id": f"https://lichess.org/{game_id}",
        "pgn": pgn,
        "played_at": played_at,
        "opponent": (opponent.get("user") or {}).get("name") or "unknown",
        "opponent_rating": opponent.get("rating"),
        "time_control": time_control,
        "result": result,
        "user_color": user_color,
    }


class LichessClient:
    def __init__(self) -> None:
        self.base = settings.lichess_api_base.rstrip("/")

    async def fetch_games(self, username: str, max_games: int = 200) -> list[dict]:
        """Most recent finished games for a user, newest first, with clocks in the PGN."""
        url = f"{self.base}/games/user/{normalize_lichess_username(username)}"
        params = {
            "max": max_games,
            "finished": "true",
            "pgnInJson": "true",
            "clocks": "true",
            "opening": "true",
        }
        headers = {"Accept": "application/x-ndjson", "User-Agent": "Sarce/0.1"}
        async with httpx.AsyncClient(timeout=120, follow_redirects=True) as client:
            res = await client.get(url, params=params, headers=headers)
            res.raise_for_status()
        return parse_ndjson(res.text)
