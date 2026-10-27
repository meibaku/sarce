from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app
from app.services.pilot import token_hash

MIGRATION = Path(__file__).resolve().parents[3] / "supabase" / "migrations" / "20261027010000_style_pilot.sql"


def test_invitation_hash_is_stable_and_not_plaintext():
    invitation_code = "this-is-a-long-one-use-invitation"
    digest = token_hash(invitation_code)
    assert len(digest) == 64 and digest != invitation_code and digest == token_hash(invitation_code)


def test_pilot_tables_are_rls_protected_and_owned_rows_cascade():
    sql = MIGRATION.read_text(encoding="utf-8").lower()
    for table in ("pilot_invitations", "pilot_consents", "pilot_read_feedback", "pilot_exit_surveys"):
        assert f"alter table public.{table} enable row level security" in sql
    assert "references public.profiles (id) on delete cascade" in sql
    assert "char_length(comment) <= 500" in sql


def test_status_requires_a_verified_user_even_when_local_mode_is_open():
    with patch("app.routers.pilot.current_user_id", return_value=None):
        response = TestClient(app).get("/pilot/status")
    assert response.status_code == 401


def test_feedback_validation_rejects_unknown_resonance():
    with patch("app.routers.pilot.current_user_id", return_value="00000000-0000-4000-8000-000000000001"):
        response = TestClient(app).put("/pilot/games/game/feedback", json={"resonance": "score"})
    assert response.status_code == 422
