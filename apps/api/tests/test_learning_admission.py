"""Admission stays balanced, anonymous at rest and bound to verified participants."""

from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app
from app.routers import learning
from app.routers.learning import participant_enrollment
from app.services.learning_admission import prepare_invite_batch, token_digest

NOW = datetime(2026, 10, 26, tzinfo=timezone.utc)
MIGRATION = Path(__file__).parents[3] / "supabase" / "migrations" / "20261026004000_learning_invitations.sql"


def test_invite_batch_is_even_balanced_and_stores_only_hashes():
    batch, invites, tokens = prepare_invite_batch(
        created_by="10000000-0000-4000-8000-000000000001", count=10,
        protocol_version=1, cohort="controlled", expires_in_hours=24, now=NOW,
    )
    assert batch["invite_count"] == 10
    assert [row["arm"] for row in invites].count("experimental") == 5
    assert [row["arm"] for row in invites].count("active_control") == 5
    assert {row["token_hash"] for row in invites} == {token_digest(token) for token in tokens}
    assert not set(tokens) & {row["token_hash"] for row in invites}


def test_invite_batch_rejects_odd_counts():
    try:
        prepare_invite_batch(
            created_by="user", count=3, protocol_version=1, cohort="controlled",
            expires_in_hours=24, now=NOW,
        )
    except ValueError as exc:
        assert "even" in str(exc)
    else:
        raise AssertionError("odd assignment batch was accepted")


def test_learning_routes_require_verified_identity():
    client = TestClient(app)
    with patch("app.routers.learning.current_user_id", return_value=None):
        assert client.get("/learning/status").status_code == 401


def test_only_configured_operator_can_issue_tokens():
    client = TestClient(app)
    with (
        patch("app.routers.learning.current_user_id", return_value="participant"),
        patch.object(learning.settings, "learning_operators", ["operator"]),
    ):
        response = client.post("/learning/invites/batches", json={"count": 2})
    assert response.status_code == 403


def test_migration_keeps_admission_server_only_and_atomic():
    sql = MIGRATION.read_text(encoding="utf-8").lower()
    assert "alter table public.learning_invites enable row level security" in sql
    assert "revoke all on function public.redeem_learning_invite" in sql
    assert "revoke all on function public.create_learning_invite_batch" in sql
    assert "for update" in sql
    assert "token_hash text not null unique" in sql


def test_participant_enrollment_conceals_assignment_and_analysis_identity():
    public = participant_enrollment({
        "id": "enrollment", "protocol_version": 1, "cohort": "controlled",
        "consented_at": NOW.isoformat(), "enrolled_at": NOW.isoformat(), "withdrawn_at": None,
        "arm": "experimental", "participant_key": "secret-analysis-key",
    })
    assert public["id"] == "enrollment"
    assert "arm" not in public
    assert "participant_key" not in public
