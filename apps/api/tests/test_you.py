"""You screen helpers (app/services/you.py)."""

from datetime import datetime, timezone
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app
from app.services import you

client = TestClient(app)


def test_time_class():
    assert you.time_class("60") == "bullet" and you.time_class("120+1") == "bullet"
    assert you.time_class("180+2") == "blitz" and you.time_class("600") == "rapid"
    assert you.time_class("1/259200") == "rapid" and you.time_class(None) == "rapid"


def test_week_index():
    end = datetime(2026, 5, 1, tzinfo=timezone.utc)
    assert you.week_index("2026-04-30T10:00:00+00:00", end) == 11
    assert you.week_index("2026-02-10T10:00:00Z", end) == 0
    assert you.week_index("2025-12-01T10:00:00Z", end) is None


def test_trait_values():
    moves = [{"signals": ["sacrifice"]}, {"signals": ["evaluation_swing"]}, {"signals": []}, {"signals": []}]
    lens = [
        {"lens": "chaos", "verdict": "real_chaos", "score": 0.2},
        {"lens": "chaos", "verdict": None, "score": 0.0},
        {"lens": "survival", "verdict": "survived"},
        {"lens": "survival", "verdict": "missed"},
    ]
    t = you.trait_values(moves, lens)
    assert t == {"Sacrifice": 0.25, "Chaos": 0.5, "Calm": 0.75, "Initiative": 0.1, "Defence": 0.5}
    assert you.trait_values([], [])["Sacrifice"] is None


def test_heat_levels_are_relative_and_empty_weeks_zero():
    assert you.heat_levels([0.1, None, 0.3, 0.2]) == [1, 0, 7, 4]
    assert you.heat_levels([None, None]) == [0, 0]
    assert you.heat_levels([0.5, 0.5]) == [4, 4]


def test_fingerprint_sentence():
    rows = {
        "Sacrifice": [0.1] * 4 + [None] * 4 + [0.2] * 4,
        "Initiative": [0.1] * 4 + [None] * 4 + [0.3] * 4,
        "Defence": [0.5] * 12,
    }
    assert you.fingerprint_sentence(rows) == "More sacrifice and initiative, with defence holding steady."
    assert you.fingerprint_sentence({"Chaos": [None] * 12}).startswith("Not enough weeks")


def test_route():
    with patch("app.routers.users.you_service.you", return_value={"games": 0}) as svc:
        assert client.get("/users/you").json() == {"games": 0}
    svc.assert_called_once()
