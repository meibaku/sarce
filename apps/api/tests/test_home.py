"""Home screen helpers: wording, honesty rules and moment selection (app/services/home.py)."""

from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app
from app.services import home

client = TestClient(app)


class TestTimeControl:
    def test_formats_and_calibration(self):
        assert home.format_time_control("60") == "1+0"
        assert home.format_time_control("180+2") == "3+2"
        assert home.format_time_control("1/259200") == "daily"
        assert home.format_time_control(None) is None
        assert home.is_calibrated("60") and home.is_calibrated("60+0")
        assert not home.is_calibrated("180") and not home.is_calibrated("60+1")


class TestStyleRead:
    def test_reads_like_the_handoff(self):
        assert home.style_read(2, 1, 1) == "You set two real problems, and one sacrifice held."

    def test_never_frames_sacrifices_as_failure(self):
        line = home.style_read(0, 2, 0)
        assert line == "You tried two sacrifices."
        assert not any(word in line.lower() for word in ("fail", "bad", "cheap", "mistake"))

    def test_partial_and_quiet(self):
        assert home.style_read(1, 3, 2) == "You set one real problem, and 2 of 3 sacrifices held."
        assert home.style_read(0, 0, 0).startswith("A quiet game")


class TestMoments:
    def test_glyphs_follow_the_copy_mapping(self):
        assert home.moment_glyph({"is_brilliant": True}, {}) == "!!"
        assert home.moment_glyph({}, {"chaos": {"verdict": "cheap_chaos"}}) == "?"
        assert home.moment_glyph({}, {"survival": {"verdict": "survived"}}) == "✓"
        assert home.moment_glyph({}, {"chaos": {"verdict": "calculated_risk"}}) == "!?"
        assert home.moment_glyph({}, {"chaos": {"verdict": None}}) is None

    def test_picks_the_three_strongest_in_game_order(self):
        moves = [{"ply": p, "san": f"m{p}", "is_brilliant": p == 9, "signals": ["sacrifice"] if p == 9 else []} for p in range(1, 12)]
        lenses = {
            3: {"chaos": {"verdict": "real_chaos", "score": 0.3}},
            5: {"chaos": {"verdict": "calculated_risk", "score": 0.05}},
            7: {"survival": {"verdict": "survived", "score": 0.4}},
            11: {"chaos": {"verdict": "real_chaos", "score": 0.2}},
        }
        picked = home.pick_moments(moves, lenses)
        assert [m["ply"] for m in picked] == [3, 7, 9]
        assert picked[2] == {"ply": 9, "san": "m9", "glyph": "!!", "line": "The sacrifice held"}


class TestBrilliantCard:
    def games(self, n, pct=4.0, total=40):
        return [{"id": str(i), "analysis": {"brilliant_pct": pct, "total_moves": total}} for i in range(n)]

    def test_hidden_below_five_games(self):
        card = home.window_brilliant(self.games(4))
        assert card["pct"] is None and card["games"] == 4

    def test_weighted_pct_and_spread(self):
        card = home.window_brilliant(self.games(10))
        assert card["pct"] == 4.0 and 0 < card["spread"] < 2

    def test_gap_line(self):
        assert home.gap_line(4.1, 6, 10) == "1.9 points below your 6–10% band."
        assert home.gap_line(7.0, 6, 10) == "Inside your 6–10% band."
        assert "after 5 analysed games" in home.gap_line(None, 6, 10)

    def test_streak_stops_at_the_first_quiet_game(self):
        games = [{"id": "a", "analysis": {}}, {"id": "b", "analysis": {"brilliant_pct": 2}}, {"id": "c", "analysis": {}}]
        assert home.style_streak(games, {"a": 1}) == 2


class TestRoute:
    def test_home_route_returns_service_payload(self):
        payload = {"latest": None, "brilliant": {"pct": None}, "stats": None}
        with patch("app.routers.users.home_service.home", return_value=payload) as svc:
            res = client.get("/users/home?username=%20Dratius%20")
        assert res.status_code == 200 and res.json() == payload
        assert svc.call_args.args[1] == "dratius"


def test_next_band_is_one_step_above_the_likely_range():
    from app.services.home import next_band

    assert next_band(0.02, 0.2) == (0.1, 0.2)  # a tiny range: one visible step toward Tal
    assert next_band(2.34, 6) == (2.4, 3.6)  # half as much again
    assert next_band(5.8, 6) == (5.8, 6)  # a fractional last step may meet the goal
    assert next_band(4.5, 6) == (4.5, 6)  # capped at the goal
    assert next_band(None, 6) is None


def test_next_band_never_passes_a_fractional_goal():
    from app.services.home import next_band

    assert next_band(0.1, 0.26) == (0.1, 0.2)


def test_session_summary_and_cutoff():
    from app.services.home import parse_since, summarise_session

    games = [
        {"id": "a", "felt_like_you": "yes", "analysis": {"brilliant_pct": 5.0}},
        {"id": "b", "felt_like_you": None, "analysis": {"brilliant_pct": 0}},
    ]
    assert summarise_session(games, {"a": 1, "b": 2}) == {"games": 2, "feltLikeYou": 1, "realProblems": 3, "brilliant": 1}
    assert summarise_session([], {}) is None
    assert parse_since("2026-10-24T10:00:00Z").isoformat() == "2026-10-24T10:00:00+00:00"
    assert parse_since("2026-10-24T10:00:00").tzinfo is not None
    assert parse_since(None) is None and parse_since("not a date") is None
