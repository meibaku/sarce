"""
Opponent scouting — Chaos Lens M8 (docs/CHAOS_PLAN.md).

Privacy rules, all enforced here:
- only usernames the user types in, and only **finished** public games;
- reports are private to the user who asked (RLS: owner only) — there is no directory;
- the fetched games are never stored, only the aggregate report;
- anyone's reports can be removed on request (`delete_target`).

Engine-free: openings, results, time controls and motif tendencies from the PGNs.
"""

from __future__ import annotations

import io
from collections import Counter

import chess
import chess.pgn

from app.db.supabase import get_supabase
from app.services.chess_com import ChessComClient, normalize_chess_com_username
from app.services.ideas import build_ply_states, find_gambits, find_king_attacks
from app.services.lichess import LichessClient, normalize_lichess_username, parse_lichess_game
from app.services.motifs import move_motifs
from app.services.pgn_parser import parse_chess_com_game
from app.services.style_profile import _pgn_opening

TABLE = "scouting_reports"
SOURCES = ("chess_com", "lichess")
MAX_GAMES = 100


def _top(counter: Counter, limit: int = 5) -> list[dict]:
    return [{"name": name, "games": count} for name, count in counter.most_common(limit)]


def build_scouting_report(parsed_games: list[dict]) -> dict:
    """
    Aggregate a player's finished games into a preparation report. Pure.

    `parsed_games` use the import shape (pgn, result, user_color, time_control), where
    "user" is the scouted player.
    """
    results: Counter[str] = Counter()
    time_controls: Counter[str] = Counter()
    openings = {"white": Counter(), "black": Counter()}
    motifs: Counter[str] = Counter()
    ideas: Counter[str] = Counter()
    moves_seen = games_read = 0

    for parsed in parsed_games:
        game = chess.pgn.read_game(io.StringIO(parsed.get("pgn") or ""))
        color = parsed.get("user_color")
        if game is None or color not in openings:
            continue
        games_read += 1
        if parsed.get("result"):
            results[parsed["result"]] += 1
        if parsed.get("time_control"):
            time_controls[parsed["time_control"]] += 1
        openings[color][_pgn_opening(parsed["pgn"])[1]] += 1

        player = chess.WHITE if color == "white" else chess.BLACK
        board, moves = game.board(), list(game.mainline_moves())
        temp = board.copy()
        for move in moves:
            if temp.turn == player:
                moves_seen += 1
                motifs.update(move_motifs(temp, move))
            temp.push(move)
        states = build_ply_states(board, moves, color, {})
        ideas["gambit"] += len(find_gambits(states))
        ideas["king_attack"] += len(find_king_attacks(states))

    per_100 = (lambda count: round(100 * count / moves_seen, 2)) if moves_seen else (lambda count: 0.0)
    return {
        "gamesSampled": games_read,
        "results": dict(results),
        "timeControls": _top(time_controls),
        "openingsAsWhite": _top(openings["white"]),
        "openingsAsBlack": _top(openings["black"]),
        # Per 100 of the player's own moves — tendencies to prepare for, not judgements.
        "motifsPer100Moves": {tag: per_100(count) for tag, count in sorted(motifs.items())},
        "ideasPerGame": {
            family: round(count / games_read, 2) if games_read else 0.0 for family, count in ideas.items()
        },
    }


def to_api(row: dict) -> dict:
    return {
        "id": row["id"],
        "username": row["target_username"],
        "source": row["source"],
        "gamesSampled": row["games_sampled"],
        "createdAt": row.get("created_at"),
        "report": row["report"],
    }


class ScoutingService:
    def __init__(self) -> None:
        self.chess_com = ChessComClient()
        self.lichess = LichessClient()

    async def _fetch_parsed(self, username: str, source: str, max_games: int) -> list[dict]:
        if source == "lichess":
            raw = await self.lichess.fetch_games(username, max_games=max_games)
            return [g for r in raw if (g := parse_lichess_game(r, username))]
        games: list[dict] = []
        for archive in reversed(await self.chess_com.fetch_recent_archives(username, limit=3)):
            batch = await self.chess_com.fetch_games_from_archive(archive)
            games.extend(g for r in reversed(batch) if (g := parse_chess_com_game(r, username)))
            if len(games) >= max_games:
                break
        return games[:max_games]

    async def create_report(self, owner_user_id: str, username: str, source: str, max_games: int = 50) -> dict:
        """Fetch the player's recent finished games, keep only the aggregate report."""
        if source not in SOURCES:
            raise ValueError(f"Unknown source {source!r}")
        normalize = normalize_lichess_username if source == "lichess" else normalize_chess_com_username
        target = normalize(username)
        parsed = await self._fetch_parsed(target, source, min(max_games, MAX_GAMES))
        report = build_scouting_report(parsed)
        res = (
            get_supabase()
            .table(TABLE)
            .upsert(
                {
                    "owner_user_id": owner_user_id,
                    "target_username": target,
                    "source": source,
                    "games_sampled": report["gamesSampled"],
                    "report": report,
                },
                on_conflict="owner_user_id,source,target_username",
            )
            .execute()
        )
        return to_api(res.data[0])

    def list_reports(self, owner_user_id: str) -> list[dict]:
        res = (
            get_supabase()
            .table(TABLE)
            .select("*")
            .eq("owner_user_id", owner_user_id)
            .order("created_at", desc=True)
            .execute()
        )
        return [to_api(row) for row in res.data or []]

    def delete_report(self, owner_user_id: str, report_id: str) -> bool:
        res = (
            get_supabase().table(TABLE).delete().eq("id", report_id).eq("owner_user_id", owner_user_id).execute()
        )
        return bool(res.data)

    def delete_target(self, source: str, username: str) -> int:
        """Deletion on request: remove every report about a player, whoever created it."""
        normalize = normalize_lichess_username if source == "lichess" else normalize_chess_com_username
        res = (
            get_supabase().table(TABLE).delete().eq("source", source).eq("target_username", normalize(username)).execute()
        )
        return len(res.data or [])
