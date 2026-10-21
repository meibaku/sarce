"""Weekly recap helpers and focus routes (app/services/recap.py)."""

from datetime import datetime
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app
from app.services import recap

client = TestClient(app)


def test_week_label():
    assert recap.week_label(datetime(2026, 10, 6), datetime(2026, 10, 12)) == "Oct 6–12"
    assert recap.week_label(datetime(2026, 9, 28), datetime(2026, 10, 4)) == "Sep 28–Oct 4"


def test_focus_line():
    assert recap.focus_line("real_problems", 3, 1, 0, 0) == "Real problems: 3 set, 3.0 : 1 sound"
    assert recap.focus_line("safe_reply", 0, 0, 2, 3) == "Safe replies: 2 of 3"
    assert recap.focus_line(None, 1, 1, 1, 1) is None


def test_streak_weeks():
    assert recap.streak_weeks([True, True, False, True]) == 2
    assert recap.streak_weeks([False]) == 0


def test_focus_routes_validate():
    with patch("app.routers.users.recap_service.set_focus", return_value={"kind": "today", "value": "sacrifice", "label": "look for a sacrifice"}) as save:
        assert client.put("/users/focus", json={"kind": "monthly", "value": "x"}).status_code == 422
        res = client.put("/users/focus", json={"kind": "today", "value": "sacrifice"})
    assert res.status_code == 200 and save.call_args.args[1:] == ("today", "sacrifice")
    with patch("app.routers.users.recap_service.set_focus", side_effect=ValueError("bad")):
        assert client.put("/users/focus", json={"kind": "weekly", "value": "nope"}).status_code == 422


def test_recap_404_without_games():
    with patch("app.routers.users.recap_service.recap", return_value=None):
        assert client.get("/users/recap").status_code == 404
