"""Serverless staging cannot accidentally start engines or background work."""

from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app


def test_request_only_runtime_refuses_engine_and_background_routes():
    with patch("app.main.settings.request_only_runtime", True):
        client = TestClient(app)
        for method, path in [
            ("post", "/games/import"), ("post", "/games/analyze"),
            ("post", "/reference/tal/process"), ("post", "/users/sync"),
            ("post", "/users/train/check"), ("post", "/scouting/reports"),
            ("post", "/play/start"), ("get", "/monitor/snapshot"),
        ]:
            response = client.post(path, json={}) if method == "post" else client.get(path)
            assert response.status_code == 503, path
            assert "request-only" in response.json()["detail"]


def test_request_only_runtime_keeps_bounded_request_routes_available():
    with patch("app.main.settings.request_only_runtime", True):
        response = TestClient(app).get("/health")
    assert response.status_code == 200
