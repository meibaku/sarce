"""Most chaotic games first (lens_service.rank_chaos_games and GET /games?chaos=true)."""

from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app
from app.services.lens_service import rank_chaos_games

client = TestClient(app)


def test_rank_by_peak_with_verdict_counts():
    peaks = [{"game_id": "b", "score": 0.47}, {"game_id": "a", "score": 0.45}, {"game_id": "b", "score": 0.30}, {"game_id": "c", "score": 0.45}]
    verdicts = [
        {"game_id": "a", "verdict": "real_chaos"},
        {"game_id": "b", "verdict": "cheap_chaos"},
        {"game_id": "b", "verdict": "calculated_risk"},
        {"game_id": "z", "verdict": "real_chaos"},  # not ranked: ignored
    ]
    ranked = rank_chaos_games(peaks, verdicts, limit=3)
    assert [g["gameId"] for g in ranked] == ["b", "a", "c"]  # a and c tie on peak; a has more real chaos
    assert ranked[0] == {"gameId": "b", "chaosPeak": 0.47, "realChaos": 0, "cheapChaos": 1, "calculatedRisk": 1}
    assert len(rank_chaos_games(peaks, verdicts, limit=1)) == 1


class _Query:
    def __init__(self, rows):
        self.rows = rows

    def __getattr__(self, _name):
        return lambda *a, **k: self

    def execute(self):
        return type("R", (), {"data": self.rows})()


def test_route_orders_most_chaotic_first():
    rows = [
        {"id": "a", "played_at": "2026-10-01", "user_color": "white", "analysis_status": "complete", "game_analyses": None},
        {"id": "b", "played_at": "2026-10-02", "user_color": "black", "analysis_status": "complete", "game_analyses": None},
    ]
    ranked = [{"gameId": "a", "chaosPeak": 0.5, "realChaos": 2, "cheapChaos": 0, "calculatedRisk": 1}, {"gameId": "b", "chaosPeak": 0.2, "realChaos": 0, "cheapChaos": 1, "calculatedRisk": 0}]
    with patch("app.routers.games.lens_service.most_chaotic_games", return_value=ranked), patch(
        "app.db.supabase.get_supabase", return_value=type("SB", (), {"table": lambda self, _t: _Query(rows)})()
    ):
        res = client.get("/games?chaos=true")
    assert res.status_code == 200
    games = res.json()["games"]
    assert [g["id"] for g in games] == ["a", "b"] and games[0]["chaosPeak"] == 0.5 and games[0]["realChaos"] == 2
    assert [g["userColor"] for g in games] == ["white", "black"]


def test_route_with_no_chaos_games_is_empty():
    with patch("app.routers.games.lens_service.most_chaotic_games", return_value=[]), patch(
        "app.db.supabase.get_supabase", return_value=type("SB", (), {"table": lambda self, _t: _Query([])})()
    ):
        assert client.get("/games?chaos=true").json() == {"games": []}
