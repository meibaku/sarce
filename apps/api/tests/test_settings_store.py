"""Settings validation and routes (app/services/settings_store.py)."""

from datetime import date
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services import settings_store

client = TestClient(app)


def test_validate_accepts_known_values():
    assert settings_store.validate({"questionBudget": 2, "theme": "system", "goalLo": 5, "goalHi": 9}) == {
        "questionBudget": 2, "theme": "system", "goalLo": 5, "goalHi": 9,
    }
    assert settings_store.validate({"quietUntil": "2026-10-25"}) == {"quietUntil": "2026-10-25"}


@pytest.mark.parametrize("bad", [{"theme": "dark"}, {"questionBudget": 3}, {"goalLo": 20}, {"goalLo": 8, "goalHi": 6}, {"nope": 1}, {"playfulMascot": "yes"}])
def test_validate_rejects(bad):
    with pytest.raises(ValueError):
        settings_store.validate(bad)


def test_quiet_until():
    assert settings_store.quiet_until(7, date(2026, 10, 18)) == "2026-10-25"


def test_settings_route_validates():
    with patch("app.routers.users.settings_store.update", side_effect=ValueError("bad")):
        assert client.put("/users/settings", json={"theme": "dark"}).status_code == 422
    with patch("app.routers.users.settings_store.update", return_value={"theme": "system"}):
        assert client.put("/users/settings", json={"theme": "system"}).json() == {"theme": "system"}
