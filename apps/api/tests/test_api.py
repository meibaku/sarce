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
