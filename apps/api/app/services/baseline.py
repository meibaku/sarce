"""
User baseline aggregation — rolling Brilliant % and move-quality distribution.

Recomputed after each game analysis. See docs/PHASES.md for phase status.
"""

from __future__ import annotations

from app.db.supabase import get_supabase

EMPTY_DISTRIBUTION = {
    "best": 0,
    "excellent": 0,
    "good": 0,
    "inaccuracy": 0,
    "mistake": 0,
    "blunder": 0,
    "miss": 0,
    "brilliant": 0,
}


class BaselineService:
    """Aggregate game analyses into user_baselines."""

    async def get_user_baseline(
        self,
        user_id: str | None = None,
        chess_com_username: str | None = None,
    ) -> dict:
        """Fetch baseline by user_id or compute from username for local dev."""
        sb = get_supabase()

        if user_id:
            res = (
                sb.table("user_baselines")
                .select("*")
                .eq("user_id", user_id)
                .maybe_single()
                .execute()
            )
            if res.data:
                return self._format_baseline(res.data)

        if chess_com_username:
            return await self._baseline_from_games(chess_com_username=chess_com_username)

        return self._empty_baseline()

    async def _baseline_from_games(
        self,
        user_id: str | None = None,
        chess_com_username: str | None = None,
    ) -> dict:
        """Compute baseline directly from completed game analyses."""
        sb = get_supabase()
        games_query = sb.table("games").select("id").eq("analysis_status", "complete")
        if user_id:
            games_query = games_query.eq("user_id", user_id)
        if chess_com_username:
            games_query = games_query.eq("chess_com_username", chess_com_username)

        games_res = games_query.execute()
        game_ids = [g["id"] for g in (games_res.data or [])]
        if not game_ids:
            return self._empty_baseline()

        analyses_res = (
            sb.table("game_analyses")
            .select("distribution, brilliant_pct")
            .in_("game_id", game_ids)
            .execute()
        )

        merged = {**EMPTY_DISTRIBUTION}
        for row in analyses_res.data or []:
            dist = row.get("distribution", {})
            for key in merged:
                merged[key] += dist.get(key, 0)

        brilliant_pct = self.brilliant_pct(merged)
        return {
            "brilliantPct": brilliant_pct,
            "distribution": merged,
            "gamesAnalyzed": len(analyses_res.data or []),
            "targetBrilliantMin": 6,
            "targetBrilliantMax": 10,
        }

    async def recompute_baseline(
        self,
        user_id: str | None = None,
        chess_com_username: str | None = None,
    ) -> dict:
        """Aggregate all completed games and upsert user_baselines."""
        computed = await self._baseline_from_games(user_id, chess_com_username)
        if computed["gamesAnalyzed"] == 0:
            return computed

        if user_id:
            sb = get_supabase()
            sb.table("user_baselines").upsert(
                {
                    "user_id": user_id,
                    "distribution": computed["distribution"],
                    "brilliant_pct": computed["brilliantPct"],
                    "games_analyzed": computed["gamesAnalyzed"],
                    "target_brilliant_min": 6,
                    "target_brilliant_max": 10,
                },
                on_conflict="user_id",
            ).execute()

        return computed

    async def get_timeline(
        self,
        user_id: str | None = None,
        chess_com_username: str | None = None,
    ) -> list[dict]:
        """Brilliant % per game over time for line chart."""
        sb = get_supabase()
        query = (
            sb.table("games")
            .select("id, played_at, opponent, game_analyses(brilliant_pct)")
            .eq("analysis_status", "complete")
            .order("played_at")
        )
        if user_id:
            query = query.eq("user_id", user_id)
        if chess_com_username:
            query = query.eq("chess_com_username", chess_com_username)

        res = query.execute()
        points = []
        for row in res.data or []:
            analyses = row.get("game_analyses")
            if not analyses:
                continue
            analysis = analyses[0] if isinstance(analyses, list) else analyses
            points.append(
                {
                    "date": row.get("played_at"),
                    "brilliantPct": float(analysis.get("brilliant_pct", 0)),
                    "opponent": row.get("opponent"),
                }
            )
        return points

    @staticmethod
    def compute_distribution(move_qualities: list[str]) -> dict:
        """Count moves per quality tier."""
        dist = {**EMPTY_DISTRIBUTION}
        for q in move_qualities:
            if q in dist:
                dist[q] += 1
        return dist

    @staticmethod
    def brilliant_pct(dist: dict) -> float:
        """Headline metric: percentage of moves classified as brilliant."""
        total = sum(dist.values())
        if total == 0:
            return 0.0
        return round((dist.get("brilliant", 0) / total) * 100, 2)

    @staticmethod
    def _format_baseline(row: dict) -> dict:
        return {
            "brilliantPct": float(row.get("brilliant_pct", 0)),
            "distribution": row.get("distribution", EMPTY_DISTRIBUTION),
            "gamesAnalyzed": row.get("games_analyzed", 0),
            "targetBrilliantMin": row.get("target_brilliant_min", 6),
            "targetBrilliantMax": row.get("target_brilliant_max", 10),
        }

    @staticmethod
    def _empty_baseline() -> dict:
        return {
            "brilliantPct": 0,
            "distribution": {**EMPTY_DISTRIBUTION},
            "gamesAnalyzed": 0,
            "targetBrilliantMin": 6,
            "targetBrilliantMax": 10,
        }
