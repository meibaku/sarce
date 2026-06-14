"""Tests for FastAPI HTTP endpoints."""

from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


class TestHealth:
    def test_health_returns_ok(self):
        res = client.get("/health")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "ok"
        assert data["service"] == "sarce-api"


class TestReferenceTal:
    @patch(
        "app.routers.reference.reference_service.get_tal_benchmark",
        new_callable=AsyncMock,
    )
    def test_tal_benchmark_endpoint(self, mock_get):
        mock_get.return_value = {
            "playerName": "Mikhail Tal",
            "brilliantPct": 0,
            "distribution": {},
            "gamesSampled": 0,
            "status": "pending",
        }
        res = client.get("/reference/tal")
        assert res.status_code == 200
        assert res.json()["playerName"] == "Mikhail Tal"


class TestGamesRoutes:
    def test_style_moments_route_exists(self):
        routes = {
            route.path
            for route in app.routes
            if "GET" in getattr(route, "methods", set())
        }

        assert "/games/moments" in routes

    def test_game_detail_route_exists(self):
        routes = {
            route.path
            for route in app.routes
            if "GET" in getattr(route, "methods", set())
        }

        assert "/games/{game_id}" in routes

    @patch("app.db.supabase.get_supabase")
    def test_game_detail_scopes_game_and_moves(self, mock_get_supabase):
        class FakeResult:
            def __init__(self, data):
                self.data = data

        class FakeQuery:
            def __init__(self, table_name, calls):
                self.table_name = table_name
                self.calls = calls

            def select(self, *_args):
                return self

            def eq(self, column, value):
                self.calls.append((self.table_name, column, value))
                return self

            def maybe_single(self):
                return self

            def order(self, *_args):
                return self

            def execute(self):
                if self.table_name == "games":
                    return FakeResult(
                        {
                            "id": "game-1",
                            "played_at": "2026-06-14T00:00:00Z",
                            "opponent": "Botvinnik",
                            "opponent_rating": 2600,
                            "result": "win",
                            "user_color": "white",
                            "time_control": "600",
                            "analysis_status": "complete",
                            "game_analyses": [
                                {
                                    "brilliant_pct": 8,
                                    "distribution": {"brilliant": 1},
                                    "total_moves": 12,
                                }
                            ],
                        }
                    )
                return FakeResult(
                    [
                        {
                            "ply": 12,
                            "uci": "h5f7",
                            "quality": "brilliant",
                            "cp_loss": 0,
                            "eval_before": 0.2,
                            "eval_after": 0.4,
                            "is_brilliant": True,
                        }
                    ]
                )

        class FakeSupabase:
            def __init__(self):
                self.calls = []

            def table(self, table_name):
                return FakeQuery(table_name, self.calls)

        fake = FakeSupabase()
        mock_get_supabase.return_value = fake

        res = client.get("/games/game-1?username=tal")

        assert res.status_code == 200
        assert res.json()["moves"][0]["quality"] == "brilliant"
        assert ("games", "chess_com_username", "tal") in fake.calls
        assert ("game_moves", "game_id", "game-1") in fake.calls
        assert ("game_moves", "games.chess_com_username", "tal") in fake.calls
