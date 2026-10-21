"""Chaos validation maths — Chaos Lens M4 (docs/CHAOS_PLAN.md). No engine or data files."""

import pytest

from app.services import chaos_validation as cv


def sample(p_fail, failed, clock="15s+", band=1400, cliff=0.5, heuristic=0.5):
    return {
        "band": band, "clock": clock, "failed": failed, "p_fail": p_fail,
        "baseline_cliff": cliff, "baseline_heuristic": heuristic,
    }


class TestBuckets:
    def test_rating_band(self):
        assert cv.rating_band(1399) == 1200
        assert cv.rating_band(1400) == 1400

    @pytest.mark.parametrize(
        "ms, bucket", [(0, "<5s"), (4_999, "<5s"), (5_000, "5-15s"), (14_999, "5-15s"), (15_000, "15s+")]
    )
    def test_clock_bucket(self, ms, bucket):
        assert cv.clock_bucket(ms) == bucket

    def test_unknown_clock(self):
        assert cv.clock_bucket(None) is None

    def test_only_one_plus_zero_counts_as_bullet(self):
        assert cv.is_bullet_1_0("60+0")
        assert not cv.is_bullet_1_0("60+1")
        assert not cv.is_bullet_1_0(None)


class TestDeciderClock:
    CLOCKS = [59_000, 58_000, 55_000, 50_000]

    def test_replier_clock_is_their_previous_annotation(self):
        # After ply 2 (White), Black replies; Black's last annotation is ply 1.
        assert cv.decider_clock_ms(self.CLOCKS, 2, 60_000) == 58_000

    def test_first_reply_uses_the_initial_time(self):
        assert cv.decider_clock_ms(self.CLOCKS, 0, 60_000) == 60_000

    def test_missing_annotation(self):
        assert cv.decider_clock_ms([59_000, None, 55_000], 2, 60_000) is None


class TestSplit:
    def test_split_is_stable_and_by_game(self):
        ids = [f"https://lichess.org/{i:08d}" for i in range(2000)]
        first = [cv.is_held_out(game_id) for game_id in ids]
        assert first == [cv.is_held_out(game_id) for game_id in ids]
        assert 0.25 < sum(first) / len(first) < 0.35


class TestBaselinesAndScores:
    def test_raw_cliff(self):
        assert cv.raw_cliff([{"ep": 0.7}, {"ep": 0.4}, {"ep": 0.1}]) == pytest.approx(0.3)
        assert cv.raw_cliff([{"ep": 0.7}]) is None

    def test_brier(self):
        samples = [sample(1.0, 1), sample(0.0, 0), sample(0.5, 1)]
        assert cv.brier(samples, "p_fail") == pytest.approx(0.25 / 3)
        assert cv.brier([], "p_fail") is None

    def test_calibration_table_groups_by_band_clock_and_bin(self):
        samples = [sample(0.82, 1), sample(0.88, 0), sample(0.12, 0), sample(0.85, 1, clock="<5s")]
        table = cv.calibration_table(samples, "p_fail")
        high = next(r for r in table if r["clock"] == "15s+" and r["bin_low"] == 0.8)
        assert high == {"band": 1400, "clock": "15s+", "bin_low": 0.8, "n": 2, "predicted": 0.85, "observed": 0.5}
        assert len(table) == 3

    def test_probability_of_one_lands_in_the_top_bin(self):
        assert cv.calibration_table([sample(1.0, 1)], "p_fail")[0]["bin_low"] == 0.9


class TestClockMultiplier:
    def test_multiplier_is_observed_over_predicted(self):
        tuning = [sample(0.2, 1, clock="<5s"), sample(0.2, 0, clock="<5s"), sample(0.4, 0), sample(0.4, 1)]
        multipliers = cv.clock_multipliers(tuning)
        assert multipliers["<5s"] == pytest.approx(2.5)
        assert multipliers["15s+"] == pytest.approx(1.25)
        assert multipliers["5-15s"] == 1.0  # no data

    def test_adjusted_probability_is_clamped(self):
        assert cv.apply_multiplier(0.6, "<5s", {"<5s": 2.5}) == 1.0
        assert cv.apply_multiplier(None, "<5s", {"<5s": 2.5}) is None


class TestSummary:
    def test_go_when_model_beats_both_baselines_on_held_out_games(self):
        tuning = [sample(0.9, 1), sample(0.1, 0)]
        held_out = [sample(0.9, 1), sample(0.1, 0), sample(0.8, 1), sample(0.2, 0)]
        summary = cv.summarize_validation(tuning, held_out)
        assert summary["beats_baselines"] is True
        assert summary["held_out_samples"] == 4
        assert summary["brier"]["p_fail_adjusted"] < summary["brier"]["baseline_cliff"]

    def test_no_go_when_model_equals_a_baseline(self):
        rows = [sample(0.5, 1), sample(0.5, 0)]
        assert cv.summarize_validation(rows, rows)["beats_baselines"] is False

    def test_clock_adjustment_alone_cannot_beat_the_same_predictor(self):
        # Model and heuristic are identical and badly scaled; the multiplier helps both equally.
        tuning = [sample(0.8, 0, heuristic=0.8), sample(0.8, 1, heuristic=0.8)]
        held_out = [sample(0.8, 0, heuristic=0.8), sample(0.8, 1, heuristic=0.8), sample(0.8, 0, heuristic=0.8)]
        summary = cv.summarize_validation(tuning, held_out)
        assert summary["clock_multipliers"]["15s+"] != 1.0
        assert summary["brier"]["p_fail_adjusted"] == summary["brier"]["baseline_heuristic_adjusted"]
        assert summary["beats_baselines"] is False

    def test_no_go_without_held_out_data(self):
        assert cv.summarize_validation([sample(0.9, 1)], [])["beats_baselines"] is False
