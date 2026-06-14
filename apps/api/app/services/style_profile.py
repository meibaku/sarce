"""Aggregate analyzed games into a player style profile."""

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


def _classify_style(signal_counts: Counter[str], distribution: dict) -> str:
    total_signals = sum(signal_counts.values()) or 1
    tactical = (
        signal_counts["tactical_resource"]
        + signal_counts["breakthrough_sacrifice"]
        + signal_counts["brilliant_sacrifice"]
        + signal_counts["momentum_shift"]
    )
    sacrifice = (
        signal_counts["sacrifice"]
        + signal_counts["exchange_sacrifice"]
        + signal_counts["breakthrough_sacrifice"]
        + signal_counts["brilliant_sacrifice"]
    )
    clean = distribution.get("best", 0) + distribution.get("excellent", 0)
    errors = (
        distribution.get("inaccuracy", 0)
        + distribution.get("mistake", 0)
        + distribution.get("blunder", 0)
        + distribution.get("miss", 0)
    )

    if sacrifice / total_signals >= 0.25:
        return "Sacrificial tactician"
    if tactical / total_signals >= 0.3:
        return "Tactical pressure player"
    if clean > errors * 2:
        return "Technical converter"
    if signal_counts["evaluation_swing"] + signal_counts["momentum_shift"] >= 3:
        return "Volatile attacker"
    return "Balanced improver"


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
                "styleLabel": "No analyzed games",
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
            "styleLabel": _classify_style(signal_counts, distribution),
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
