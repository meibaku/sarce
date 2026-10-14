"""Most-chaotic-first game list: ranking helper and the /games?chaos=true route."""

from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app
from app.services.lens_service import rank_chaos_games

client = TestClient(app)


def row(game, score, verdict=None):
    return {"game_id": game, "score": score, "verdict": verdict}


class TestRankChaosGames:
    def test_orders_by_peak_and_counts_verdicts(self):
        rows = [
            row("a", 0.10, "cheap_chaos"),
            row("b", 0.45, "real_chaos"),
            row("b", 0.02),
            row("a", 0.30, "real_chaos"),
            row("c", None),
        ]
        ranked = rank_chaos_games(rows, limit=10)
        assert [g["gameId"] for g in ranked] == ["b", "a", "c"]
        assert ranked[1] == {
            "gameId": "a", "chaosPeak": 0.30, "realChaos": 1, "cheapChaos": 1, "calculatedRisk": 0,
        }

    def test_ties_put_more_real_chaos_first_and_limit_applies(self):
        rows = [row("x", 0.2, "cheap_chaos"), row("y", 0.2, "real_chaos"), row("z", 0.1)]
        assert [g["gameId"] for g in rank_chaos_games(rows, limit=2)] == ["y", "x"]


class _GamesQuery:
    """Stand-in for the games query: records `in_` and returns the stored rows."""

    def __init__(self, rows):
        self.rows, self.in_ids = rows, None

    def __getattr__(self, _name):
        return lambda *args, **kwargs: self

    def in_(self, _column, ids):
        self.in_ids = ids
        return self

    def execute(self):
        return type("Res", (), {"data": [r for r in self.rows if self.in_ids is None or r["id"] in self.in_ids]})()


def game(gid, played_at):
    return {"id": gid, "played_at": played_at, "opponent": gid, "opponent_rating": 1500, "result": "win",
            "time_control": "60", "analysis_status": "complete", "game_analyses": None}


class TestChaosGameList:
    def test_returns_only_ranked_games_most_chaotic_first(self):
        # The database returns newest first; the route must reorder by chaos.
        query = _GamesQuery([game("new", "2026-10-02"), game("old", "2026-01-01"), game("plain", "2026-10-03")])
        ranked = [
            {"gameId": "old", "chaosPeak": 0.47, "realChaos": 0, "cheapChaos": 3, "calculatedRisk": 0},
            {"gameId": "new", "chaosPeak": 0.12, "realChaos": 1, "cheapChaos": 0, "calculatedRisk": 0},
        ]
        with patch("app.db.supabase.get_supabase", return_value=type("Sb", (), {"table": lambda _s, _t: query})()), \
             patch("app.routers.games.lens_service.most_chaotic_games", return_value=ranked):
            res = client.get("/games?chaos=true")
        assert res.status_code == 200
        games = res.json()["games"]
        assert [g["id"] for g in games] == ["old", "new"]
        assert games[0]["chaosPeak"] == 0.47 and games[0]["cheapChaos"] == 3

    def test_no_chaos_data_returns_an_empty_list(self):
        query = _GamesQuery([game("plain", "2026-10-03")])
        with patch("app.db.supabase.get_supabase", return_value=type("Sb", (), {"table": lambda _s, _t: query})()), \
             patch("app.routers.games.lens_service.most_chaotic_games", return_value=[]):
            assert client.get("/games?chaos=true").json() == {"games": []}
