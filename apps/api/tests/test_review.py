"""Review helpers and routes (app/services/review.py)."""

from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app
from app.services import review

client = TestClient(app)

DETAILS = {"p_fail": {"100": 0.7, "800": 0.82, "1200": 0.71, "1600": 0.58, "2000": 0.41, "2400": 0.26}, "safe_set": ["g8h8"]}


class TestLadder:
    def test_reads_the_five_rungs(self):
        assert review.ladder_p_fail(DETAILS) == [0.82, 0.71, 0.58, 0.41, 0.26]
        assert review.ladder_p_fail({"p_fail": {"800": 0.5}}) is None
        assert review.ladder_p_fail(None) is None

    def test_falls_line(self):
        pf = review.ladder_p_fail(DETAILS)
        assert review.falls_line("set", pf, 1580, True) == "At 1600, about 6 in 10 players miss the safe reply here."
        assert review.falls_line("survived", pf, 1650, True).endswith("You found the safe reply.")
        assert "uncalibrated" in review.falls_line("set", pf, 1600, False)
        assert review.falls_line("set", None, 1600, True) == "No human-model data for this move."


class TestWording:
    def test_questions_and_mirror_never_grade(self):
        assert review.ask_for("!!", "set", True) == "You gave up material. What were you going for?"
        assert review.ask_for("✓", "survived", False) == "Did you see the trap, or was it instinct?"
        sound = review.mirror_line(0.02, "Rxe5", "Rxe5")
        assert sound.startswith("Sound:")
        costly = review.mirror_line(0.3, "Qe2", "Kh1")
        assert costly == "The engine preferred Qe2, 0.30 expected points better."
        for line in (sound, costly):
            assert not any(w in line.lower() for w in ("blunder", "mistake", "bad", "fail"))


class TestSquaresAndPlans:
    def test_hot_squares(self):
        assert review.hot_squares("set", "e1e5", ["f6f7"], None) == ["e5", "f7", "e1"]
        assert review.hot_squares("survived", "e1e2", [], "d8h4") == ["e2", "h4", "e1"]

    def test_plan_outcome(self):
        ideas = [{"start_ply": 26, "end_ply": 46, "verdict": "worked"}, {"start_ply": 50, "end_ply": 60, "verdict": "fizzled"}]
        assert review.plan_outcome(36, ideas) == "Your plan happened: the idea landed by move 24."
        assert review.plan_outcome(55, ideas) is None


class TestRoutes:
    def test_review_404(self):
        with patch("app.routers.games.review_service.review", return_value=None):
            assert client.get("/games/x/review").status_code == 404

    def test_intent_validates_and_saves(self):
        with patch("app.routers.games.review_service.save_intent", return_value={"type": "bluff", "note": "go"}) as save:
            assert client.put("/games/g/moves/36/intent", json={"type": "guess"}).status_code == 422
            res = client.put("/games/g/moves/36/intent", json={"type": "bluff", "note": "go"})
        assert res.status_code == 200 and res.json() == {"type": "bluff", "note": "go"}
        assert save.call_args.args[:4] == ("g", 36, "bluff", "go")
