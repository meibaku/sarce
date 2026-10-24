"""
Aggregate analyzed games into a player style profile: openings, phases, signals, results and quality mix.

There is deliberately no one-word style label: the hand-cut thresholds it used were never validated (review
F11b). Style is the fingerprint's traits on You; percentile traits replace them once validated (plan 2.4).
"""

from __future__ import annotations

from collections import Counter
import io

import chess.pgn

from app.db.supabase import get_supabase
from app.services.baseline import BaselineService


def _pgn_opening(pgn_text: str) -> tuple[str | None, str]:
    game = chess.pgn.read_game(io.StringIO(pgn_text))
    if game is None:
        return None, "Unknown opening"
    eco = game.headers.get("ECO") or None
    opening = (
        game.headers.get("Opening")
        or game.headers.get("Variation")
        or game.headers.get("ECOUrl", "").rstrip("/").split("/")[-1].replace("-", " ")
        or "Unknown opening"
    )
    return eco, opening


class StyleProfileService:
    async def get_profile(
        self,
        user_id: str | None = None,
        chess_com_username: str | None = None,
    ) -> dict:
        sb = get_supabase()
        games_query = (
            sb.table("games")
            .select("id, pgn, result, time_control, opponent_rating")
            .eq("analysis_status", "complete")
            .neq("source", "sarce_bot")  # bot games are practice
        )
        if user_id:
            games_query = games_query.eq("user_id", user_id)
        if chess_com_username:
            games_query = games_query.eq("chess_com_username", chess_com_username)

        games_res = games_query.execute()
        games = games_res.data or []
        game_ids = [game["id"] for game in games]
        if not game_ids:
            return {
                "gamesAnalyzed": 0,
                "favoriteOpening": None,
                "openings": [],
                "phaseDistribution": {},
                "signalDistribution": {},
                "resultDistribution": {},
                "timeControlDistribution": {},
                "qualityDistribution": {**BaselineService.compute_distribution([])},
            }

        moves_res = (
            sb.table("game_moves")
            .select("quality, phase, signals")
            .in_("game_id", game_ids)
            .execute()
        )

        opening_counts: Counter[str] = Counter()
        opening_meta: dict[str, dict] = {}
        result_counts: Counter[str] = Counter()
        time_counts: Counter[str] = Counter()
        signal_counts: Counter[str] = Counter()
        phase_counts: Counter[str] = Counter()
        qualities: list[str] = []

        for game in games:
            eco, opening = _pgn_opening(game.get("pgn") or "")
            opening_counts[opening] += 1
            opening_meta[opening] = {"eco": eco, "name": opening}
            if game.get("result"):
                result_counts[game["result"]] += 1
            if game.get("time_control"):
                time_counts[game["time_control"]] += 1

        for move in moves_res.data or []:
            if move.get("quality"):
                qualities.append(move["quality"])
            if move.get("phase"):
                phase_counts[move["phase"]] += 1
            signal_counts.update(move.get("signals") or [])

        distribution = BaselineService.compute_distribution(qualities)
        favorite_opening = opening_counts.most_common(1)[0][0] if opening_counts else None

        return {
            "gamesAnalyzed": len(games),
            "favoriteOpening": opening_meta.get(favorite_opening) if favorite_opening else None,
            "openings": [
                {**opening_meta[name], "games": count}
                for name, count in opening_counts.most_common(8)
            ],
            "phaseDistribution": dict(phase_counts),
            "signalDistribution": dict(signal_counts),
            "resultDistribution": dict(result_counts),
            "timeControlDistribution": dict(time_counts),
            "qualityDistribution": distribution,
        }
