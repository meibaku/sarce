"""Expected-points helpers — Chaos Lens M1 (docs/CHAOS_PLAN.md)."""

import pytest

from app.services.ep import cp_to_ep, is_decided, line_ep, mate_to_ep, wdl_to_ep


class TestWdlToEp:
    def test_per_mille_wdl(self):
        assert wdl_to_ep(500, 300, 200) == pytest.approx(0.65)

    def test_certain_outcomes(self):
        assert wdl_to_ep(1000, 0, 0) == 1.0
        assert wdl_to_ep(0, 1000, 0) == 0.5
        assert wdl_to_ep(0, 0, 1000) == 0.0

    @pytest.mark.parametrize("wdl", [(0, 0, 0), (-1, 500, 501)])
    def test_rejects_invalid_counts(self, wdl):
        with pytest.raises(ValueError):
            wdl_to_ep(*wdl)


class TestCpToEp:
    def test_equal_position_is_half(self):
        assert cp_to_ep(0) == pytest.approx(0.5)

    def test_symmetric_and_monotonic(self):
        assert cp_to_ep(150) + cp_to_ep(-150) == pytest.approx(1.0)
        assert cp_to_ep(-300) < cp_to_ep(-50) < cp_to_ep(50) < cp_to_ep(300)

    def test_extreme_scores_do_not_overflow(self):
        assert cp_to_ep(1_000_000) == pytest.approx(1.0)
        assert cp_to_ep(-1_000_000) == pytest.approx(0.0)


class TestMateToEp:
    def test_mating_side_wins(self):
        assert mate_to_ep(3) == 1.0

    def test_mated_side_loses(self):
        assert mate_to_ep(-2) == 0.0
        assert mate_to_ep(0) == 0.0


class TestLineEp:
    def test_prefers_wdl_over_score(self):
        assert line_ep([200, 600, 200], cp=900, mate=None) == pytest.approx(0.5)

    def test_falls_back_to_mate_then_cp(self):
        assert line_ep(None, cp=None, mate=-4) == 0.0
        assert line_ep(None, cp=0, mate=None) == pytest.approx(0.5)

    def test_none_without_any_score(self):
        assert line_ep(None, cp=None, mate=None) is None


class TestIsDecided:
    def test_inside_band_is_live(self):
        assert not is_decided(0.5, 0.05, 0.95)
        assert not is_decided(0.05, 0.05, 0.95)

    def test_outside_band_is_decided(self):
        assert is_decided(0.97, 0.05, 0.95)
        assert is_decided(0.01, 0.05, 0.95)

    def test_unknown_ep_is_not_decided(self):
        assert not is_decided(None, 0.05, 0.95)
