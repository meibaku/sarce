"""Tests for baseline aggregation helpers."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.baseline import BaselineService, EMPTY_DISTRIBUTION
from app.services.style_goals import TAL_GOAL_MAX, TAL_GOAL_MIN


class TestBaselineHelpers:
    def test_compute_distribution(self):
        dist = BaselineService.compute_distribution(
            ["best", "best", "brilliant", "mistake"]
        )
        assert dist["best"] == 2
        assert dist["brilliant"] == 1
        assert dist["mistake"] == 1
        assert dist["blunder"] == 0

    def test_brilliant_pct(self):
        dist = {**EMPTY_DISTRIBUTION, "brilliant": 2, "best": 8}
        assert BaselineService.brilliant_pct(dist) == 20.0

    def test_brilliant_pct_empty(self):
        assert BaselineService.brilliant_pct(EMPTY_DISTRIBUTION) == 0.0

    def test_style_vector_v1(self):
        from app.services.analysis import build_style_vector_v1

        dist = {**EMPTY_DISTRIBUTION, "brilliant": 1, "best": 9}
        vec = build_style_vector_v1(dist, 10.0)
        assert vec["version"] == 1
        assert vec["brilliantPct"] == 10.0
        assert vec["sacrificeRate"] == 0.1

    def test_style_vector_tactical_complexity_uses_emitted_signals(self):
        from app.services.analysis import build_style_vector_v1

        dist = {**EMPTY_DISTRIBUTION, "best": 2, "mistake": 2}
        vec = build_style_vector_v1(
            dist,
            0.0,
            [
                {"signals": ["tactical_resource"]},
                {"signals": ["momentum_shift"]},
                {"signals": ["clean_move"]},
                {"signals": []},
            ],
        )

        assert vec["tacticalComplexity"] == 0.5

    def test_recompute_preserves_a_custom_stored_goal(self):
        service = BaselineService()
        computed = {
            "brilliantPct": 0.3,
            "distribution": {**EMPTY_DISTRIBUTION, "brilliant": 1},
            "gamesAnalyzed": 1,
            "targetBrilliantMin": TAL_GOAL_MIN,
            "targetBrilliantMax": TAL_GOAL_MAX,
        }
        service._baseline_from_games = AsyncMock(return_value=computed)
        supabase = MagicMock()

        with patch("app.services.baseline.get_supabase", return_value=supabase):
            asyncio.run(service.recompute_baseline(user_id="owner"))

        row = supabase.table.return_value.upsert.call_args.args[0]
        assert "target_brilliant_min" not in row
        assert "target_brilliant_max" not in row
