"""One focus a week (app/services/focus.py, plan 3.2)."""

from app.services import focus as f
from app.services.recap import FOCUSES, focus_line


def test_pick_takes_the_trait_with_the_most_room_and_skips_thin_ones():
    weekly = {"Grip": [0.8, 0.82, 0.85, 0.84, 0.83, 0.86, 0.81], "Chaos": [0.2, 0.18, 0.22, 0.19, 0.21, 0.2, 0.23], "Fight": [0.3, None, None, None, None, None, 0.1]}
    recent = {"Grip": 0.79, "Chaos": 0.21, "Fight": 0.05}
    assert f.pick_trait(weekly, recent) == "Grip"  # below every week; Fight has too few weeks to count


def test_target_comes_from_your_own_range():
    assert f.target_for("Grip", 0.8, 400, [0.8]) > 0.8  # the 95% range's upper end
    assert f.target_for("Initiative", 0.09, 0, [0.05, 0.08, 0.1, 0.12]) == 0.1  # 75th-percentile week


def test_verdict_only_moves_when_ranges_separate():
    assert f.week_verdict("Grip", (0.95, 400), (0.80, 1600)) == "up"
    assert f.week_verdict("Grip", (0.81, 40), (0.80, 1600)) == "held"
    assert f.week_verdict("Initiative", (0.2, 400), (0.05, 400)) == "held"  # a mean, no range


def test_trait_focus_values_and_recap_line():
    assert f.trait_from_focus("trait:Grip") == "Grip" and f.trait_from_focus("real_problems") is None and f.trait_from_focus("trait:Brilliant") is None
    assert "trait:Grip" in FOCUSES and not any("Brilliant" in k for k in FOCUSES)
    line = focus_line("trait:Grip", 0, 0, 0, 0, {"trait": "Grip", "verdict": "up", "value": 0.84, "target": 0.88, "unit": "share"})
    assert line == "Grip moved up: 84%, aiming for 88%"


def test_windows_and_this_week():
    ids = [f"g{i}" for i in range(100)]
    w = f.windows_of(ids)
    assert len(w) == 3 and w[-1][0] == "g0" and len(w[0]) == 20
    games = [{"id": "c", "played_at": "2026-10-20T10:00:00+00:00"}, {"id": "b", "played_at": "2026-10-14T11:00:00+00:00"}, {"id": "a", "played_at": "2026-10-01T10:00:00+00:00"}]
    assert f.this_week(games) == ["c", "b"]
