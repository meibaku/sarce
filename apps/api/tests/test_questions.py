"""After-game questions and intention grading (app/services/questions.py)."""

from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app
from app.services import questions as q

client = TestClient(app)


def test_rotation_respects_budget_and_is_stable():
    assert q.rotation("game-a", 0) == []
    one = q.rotation("game-a", 1)
    assert len(one) == 1 and one == q.rotation("game-a", 1)
    two = q.rotation("game-a", 2)
    assert len(two) == 2 and len(set(two)) == 2 and two[0] == one[0]
    starts = {q.rotation(f"g{i}", 1)[0] for i in range(30)}
    assert starts == {"felt", "intent", "checkin"}


def test_checkin_prefers_flags_else_control():
    assert q.checkin_target("g", [14, 20], [2, 4, 14]) == (14, True)
    ply, flagged = q.checkin_target("g", [], [2, 4, 6])
    assert ply in (2, 4, 6) and flagged is False
    assert q.checkin_target("g", [], []) == (None, False)


def test_intention_for_uses_the_latest_before_the_game():
    intents = [
        {"value": "solid", "set_at": "2026-10-17T08:00:00Z"},
        {"value": "sacrifice", "set_at": "2026-10-18T09:00:00Z"},
        {"value": "calm", "set_at": "2026-10-18T12:00:00Z"},
    ]
    assert q.intention_for(intents, "2026-10-18T10:00:00Z") == "sacrifice"
    assert q.intention_for(intents, "2026-10-20T10:00:00Z") is None
    assert q.intention_for(intents, None) is None


def test_grade_intention_mirrors():
    g = q.grade_intention("sacrifice", ["19. Rxe5"], 0, 0, 0, 0)
    assert g["met"] is True and "19. Rxe5" in g["line"]
    assert q.grade_intention("sacrifice", [], 0, 0, 0, 0)["met"] is False
    assert q.grade_intention("calm", [], 0, 0, 0, 0)["met"] is None
    assert q.grade_intention("calm", [], 2, 1, 0, 0)["line"] == "You found the safe reply 2 of 3 times."
    assert q.grade_intention("solid", [], 0, 0, 1, 1)["met"] is False
    assert q.grade_intention(None, [], 0, 0, 0, 0) is None


def test_checkin_route_validates():
    with patch("app.routers.games.summary_service.set_checkin", side_effect=ValueError("bad")):
        assert client.post("/games/g/checkin", json={"ply": 4, "answer": "bored"}).status_code == 422
    with patch("app.routers.games.summary_service.set_checkin") as save:
        res = client.post("/games/g/checkin", json={"ply": 4, "answer": "distracted", "flagged": True})
    assert res.status_code == 200 and save.call_args.args == ("g", 4, "distracted", True)
