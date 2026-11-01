from pathlib import Path
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app
from app.services.pilot import PILOT_READ_TARGET, PilotService, lifecycle, token_hash

MIGRATION = Path(__file__).resolve().parents[3] / "supabase" / "migrations" / "20261027010000_style_pilot.sql"


def test_invitation_hash_is_stable_and_not_plaintext():
    invitation_code = "invite-" + ("x" * 32)
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


def test_public_mode_does_not_expose_participant_state():
    response = TestClient(app).get("/public/pilot")
    assert response.status_code == 200
    assert "admitted" not in response.json()
    assert "completedReads" not in response.json()


def test_feedback_validation_rejects_unknown_resonance():
    with patch("app.routers.pilot.current_user_id", return_value="00000000-0000-4000-8000-000000000001"):
        response = TestClient(app).put("/pilot/games/game/feedback", json={"resonance": "score"})
    assert response.status_code == 422


def test_lifecycle_uses_first_ten_reads_and_the_consent_deadline():
    started = datetime(2026, 10, 1, tzinfo=timezone.utc)
    feedback = [
        {"id": str(index), "created_at": (started + timedelta(minutes=index)).isoformat(), "resonance": "yes"}
        for index in range(11)
    ]
    feedback[10]["resonance"] = "no"
    state = lifecycle(
        {"consented_at": started.isoformat(), "withdrawn_at": None},
        list(reversed(feedback)),
        started + timedelta(days=1),
    )
    assert state["state"] == "complete"
    assert state["completedReads"] == PILOT_READ_TARGET
    assert state["answers"] == {"yes": 10, "partly": 0, "no": 0}
    assert state["endsAt"] == (started + timedelta(days=14)).isoformat()


def test_lifecycle_expires_at_fourteen_days_and_withdrawal_wins():
    started = datetime(2026, 10, 1, tzinfo=timezone.utc)
    consent = {"consented_at": started.isoformat(), "withdrawn_at": None}
    assert lifecycle(consent, [], started + timedelta(days=14))["state"] == "expired"
    consent["withdrawn_at"] = (started + timedelta(days=2)).isoformat()
    assert lifecycle(consent, [], started + timedelta(days=14))["state"] == "withdrawn"


class ScriptedClient:
    """Small fluent Supabase stand-in; each execute consumes one declared result."""

    def __init__(self, results):
        self.results = list(results)

    def table(self, _name):
        return self

    def __getattr__(self, _name):
        return lambda *_args, **_kwargs: self

    def execute(self):
        return SimpleNamespace(data=self.results.pop(0))


def consent_row(days_ago=1):
    return {
        "protocol_version": "style-v1",
        "privacy_version": "pilot-privacy-v1",
        "consented_at": (datetime.now(timezone.utc) - timedelta(days=days_ago)).isoformat(),
        "withdrawn_at": None,
    }


def completed_feedback():
    now = datetime.now(timezone.utc)
    return [
        {"id": str(index), "resonance": "yes", "created_at": (now - timedelta(minutes=index)).isoformat()}
        for index in range(10)
    ]


def test_eleventh_distinct_feedback_is_rejected_but_an_existing_read_can_be_edited():
    rejected = PilotService(ScriptedClient([
        [{"id": "game"}], [consent_row()], completed_feedback(), [{"id": "invite"}], [],
    ]))
    try:
        rejected.feedback("user", "game", "no", None)
    except ValueError as exc:
        assert "at most 10" in str(exc)
    else:
        raise AssertionError("an eleventh distinct read was accepted")

    updated = {
        "id": "answer",
        "game_id": "game",
        "resonance": "partly",
        "comment": "Closer than before",
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    service = PilotService(ScriptedClient([
        [{"id": "game"}], [consent_row()], completed_feedback(), [{"id": "invite"}],
        [{**updated, "created_at": datetime.now(timezone.utc).isoformat()}], [updated],
    ]))
    assert service.feedback("user", "game", "partly", "Closer than before") == {
        "id": "answer",
        "gameId": "game",
        "resonance": "partly",
        "comment": "Closer than before",
        "savedAt": updated["updated_at"],
    }


def test_feedback_lookup_rejects_a_game_owned_by_another_participant():
    service = PilotService(ScriptedClient([[]]))
    try:
        service.get_feedback("user-a", "user-b-game")
    except ValueError as exc:
        assert str(exc) == "Game not found"
    else:
        raise AssertionError("cross-tenant feedback was exposed")


def test_feedback_route_hides_cross_tenant_game(monkeypatch):
    monkeypatch.setattr("app.routers.pilot.current_user_id", lambda: "user-a")
    monkeypatch.setattr(
        "app.routers.pilot.PilotService",
        lambda: type("MissingGame", (), {
            "get_feedback": lambda _service, _owner, _game: (
                _ for _ in ()
            ).throw(ValueError("Game not found"))
        })(),
    )
    response = TestClient(app).get("/pilot/games/user-b-game/feedback")
    assert response.status_code == 404


def test_admission_fails_closed_until_legal_and_release_approval(monkeypatch):
    monkeypatch.setattr("app.services.pilot.settings.pilot_admission_open", False)
    service = PilotService(ScriptedClient([]))
    for action in (
        lambda: service.create_invitation("operator"),
        lambda: service.redeem("user", "long-enough-invitation-code"),
        lambda: service.consent("user", True, "style-v1", "pilot-privacy-v1"),
    ):
        try:
            action()
        except ValueError as exc:
            assert str(exc) == "Pilot admission is not open"
        else:
            raise AssertionError("admission bypassed the approval gate")
