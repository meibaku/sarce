"""Tests for baseline aggregation helpers."""

from app.services.baseline import BaselineService, EMPTY_DISTRIBUTION


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
