"""Honest uncertainty (app/services/uncertainty.py, review F4)."""

from app.services import home, you
from app.services.uncertainty import MIN_EVENTS, direction, gated, wilson


def test_wilson_is_sane_near_zero_and_matches_the_review_table():
    lo, hi = wilson(0, 175)
    assert lo == 0.0 and 0.015 < hi < 0.03  # no negative lower bound at zero events
    # Five bullet games (~175 moves) at a true 2% vs 6% overlap: the same window can't tell them apart.
    two, six = wilson(3.5, 175), wilson(10.5, 175)
    assert direction(two, six) is None
    assert wilson(0, 0) is None


def test_direction_only_when_intervals_separate():
    assert direction((0.01, 0.02), (0.03, 0.05)) == "up"
    assert direction((0.03, 0.05), (0.01, 0.02)) == "down"
    assert direction((0.01, 0.04), (0.03, 0.05)) is None


def test_gated_dashes_thin_rates():
    assert gated(0.5, MIN_EVENTS - 1) is None and gated(0.5, MIN_EVENTS) == 0.5


def g(total, pct, at):
    return {"played_at": at, "analysis": {"total_moves": total, "brilliant_pct": pct}}


def test_window_and_rolling_brilliant_carry_intervals():
    games = [g(35, 4.0, f"2026-10-{d:02d}") for d in range(30, 0, -1)]  # 30 games, newest first
    w = home.window_brilliant(games)
    assert w["lo"] < w["pct"] < w["hi"] and w["moves"] == 1050
    rolling = home.rolling_brilliant(games)
    # Windows of 20 every 5 games over 30 games: ends at 30, 25, 20.
    assert len(rolling) == 3 and rolling[-1]["endAt"] == "2026-10-30" and all(p["lo"] <= p["pct"] <= p["hi"] for p in rolling)


def test_traits_under_min_events_are_dashed():
    moves = [{"signals": []}] * 40
    lens = [{"lens": "squeeze", "verdict": "kept", "score": 1.0}] * 5  # five winning positions: too few for Grip
    values, events = you.gated_traits(moves, lens)
    assert events["Grip"] == 5 and values["Grip"] is None
    assert values["Calm"] == 1.0  # 40 moves is enough for a per-move trait
