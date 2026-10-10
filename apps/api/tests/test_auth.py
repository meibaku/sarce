"""Optional sign-in — Chaos Lens M8. Supabase Auth is mocked; no network."""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app import deps
from app.config import settings
from app.main import app

client = TestClient(app)
ALICE, MALLORY = "11111111-1111-4111-8111-111111111111", "99999999-9999-4999-8999-999999999999"


def supabase_with_user(user_id: str | None):
    """A stand-in client whose auth.get_user returns `user_id`, or raises when None."""
    sb = MagicMock()
    if user_id is None:
        sb.auth.get_user.side_effect = RuntimeError("bad token")
    else:
        sb.auth.get_user.return_value = SimpleNamespace(user=SimpleNamespace(id=user_id))
    return sb


@pytest.fixture(autouse=True)
def reset_auth_state(monkeypatch):
    monkeypatch.setattr(settings, "auth_required", False)
    deps._current_user.set(None)
    yield
    deps._current_user.set(None)


class TestAuthenticate:
    @patch("app.routers.scouting.scouting_service.list_reports", return_value=[])
    def test_local_first_without_a_token(self, mock_list):
        assert client.get("/scouting/reports").status_code == 200
        mock_list.assert_called_once_with(settings.local_user_id)

    @patch("app.routers.scouting.scouting_service.list_reports", return_value=[])
    def test_token_identity_overrides_a_client_supplied_user_id(self, mock_list):
        with patch("app.deps.get_supabase", return_value=supabase_with_user(ALICE)):
            res = client.get(f"/scouting/reports?user_id={MALLORY}", headers={"Authorization": "Bearer good"})
        assert res.status_code == 200
        mock_list.assert_called_once_with(ALICE)

    def test_invalid_token_is_rejected_even_when_sign_in_is_optional(self):
        with patch("app.deps.get_supabase", return_value=supabase_with_user(None)):
            res = client.get("/scouting/reports", headers={"Authorization": "Bearer forged"})
        assert res.status_code == 401

    def test_required_mode_rejects_anonymous_requests(self, monkeypatch):
        monkeypatch.setattr(settings, "auth_required", True)
        assert client.get("/scouting/reports").status_code == 401
        assert client.get("/traps").status_code == 401
        assert client.get("/games").status_code == 401
        assert client.get("/health").status_code == 200

    @pytest.mark.parametrize("header", ["Basic abc", "Bearer ", "token-without-scheme"])
    def test_malformed_headers_count_as_no_token(self, header, monkeypatch):
        monkeypatch.setattr(settings, "auth_required", True)
        assert client.get("/scouting/reports", headers={"Authorization": header}).status_code == 401

    @patch("app.routers.scouting.scouting_service.list_reports", return_value=[])
    def test_identity_does_not_leak_into_the_next_request(self, mock_list):
        with patch("app.deps.get_supabase", return_value=supabase_with_user(ALICE)):
            client.get("/scouting/reports", headers={"Authorization": "Bearer good"})
        client.get("/scouting/reports")
        assert [call.args[0] for call in mock_list.call_args_list] == [ALICE, settings.local_user_id]


class TestScoping:
    def test_scoped_user_id_local_first_keeps_the_old_behaviour(self):
        assert deps.scoped_user_id(None, "hikaru") is None
        assert deps.scoped_user_id(None, None) == settings.local_user_id
        assert deps.scoped_user_id("u-1", "hikaru") == "u-1"

    def test_scoped_user_id_signed_in_is_always_the_caller(self):
        deps._current_user.set(ALICE)
        assert deps.scoped_user_id(None, "hikaru") == ALICE
        assert deps.scoped_user_id(MALLORY, "hikaru") == ALICE
        assert deps.resolve_user_id(MALLORY) == ALICE

    def test_game_access_is_a_no_op_when_local_first(self):
        deps.require_game_access("any-game")  # must not raise or touch the database

    @patch("app.routers.games.lens_service.get_game_lenses", return_value=[])
    @patch("app.routers.games.lens_service.get_game_clocks", return_value=None)
    def test_signed_in_user_cannot_read_another_users_game(self, _clocks, mock_lenses):
        sb = supabase_with_user(ALICE)
        owned = sb.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute
        owned.return_value = SimpleNamespace(data=[])
        with patch("app.deps.get_supabase", return_value=sb):
            res = client.get("/games/someone-elses/lenses", headers={"Authorization": "Bearer good"})
            assert res.status_code == 404
            mock_lenses.assert_not_called()
            owned.return_value = SimpleNamespace(data=[{"id": "mine"}])
            assert client.get("/games/mine/lenses", headers={"Authorization": "Bearer good"}).status_code == 200

    @patch("app.routers.users.lens_service.chaos_summary", return_value={})
    def test_chaos_summary_is_narrowed_to_the_signed_in_user(self, mock_summary):
        with patch("app.deps.get_supabase", return_value=supabase_with_user(ALICE)):
            client.get("/users/hikaru/chaos-summary", headers={"Authorization": "Bearer good"})
        mock_summary.assert_called_once_with("hikaru", user_id=ALICE)
