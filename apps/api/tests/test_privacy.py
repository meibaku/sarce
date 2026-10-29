from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app
from app.services.privacy import OWNED_TABLES, reapply_deletions, receipt_hash

MIGRATION = Path(__file__).resolve().parents[3] / "supabase" / "migrations" / "20261027011000_account_deletion_jobs.sql"
TOMBSTONE_MIGRATION = Path(__file__).resolve().parents[3] / "supabase" / "migrations" / "20261029010000_pilot_deletion_tombstones.sql"


def test_deletion_receipts_are_hashed_and_jobs_survive_user_removal():
    sql = MIGRATION.read_text(encoding="utf-8").lower()
    assert "references auth.users" not in sql
    assert "enable row level security" in sql
    assert len(receipt_hash("opaque-deletion-receipt")) == 64
    tombstones = TOMBSTONE_MIGRATION.read_text(encoding="utf-8").lower()
    assert "references auth.users" not in tombstones
    assert "enable row level security" in tombstones


def test_export_contract_covers_direct_and_derived_owner_tables():
    assert {"pilot_consents", "pilot_read_feedback", "shared_links", "analysis_jobs"} <= set(OWNED_TABLES)


def test_export_and_delete_require_a_verified_user():
    client = TestClient(app)
    with patch("app.routers.privacy.current_user_id", return_value=None):
        assert client.get("/privacy/me/export").status_code == 401
        assert client.delete("/privacy/me?confirm=DELETE").status_code == 401


def test_delete_requires_explicit_confirmation_before_service_work():
    with patch("app.routers.privacy.current_user_id", return_value="user"):
        response = TestClient(app).delete("/privacy/me?confirm=no")
    assert response.status_code == 422


def test_restore_check_reapplies_completed_tombstones_before_passing():
    present = {"deleted-user"}
    recorded = []
    result = reapply_deletions(
        [{"jobId": "job", "userId": "deleted-user", "receiptHash": "a" * 64, "completedAt": "2026-10-29T00:00:00Z"}],
        lambda user_id: user_id in present,
        lambda user_id: present.remove(user_id),
        lambda row, checked_at: recorded.append((row["jobId"], checked_at)),
    )
    assert result["status"] == "passed" and result["reapplied"] == 1 and result["remaining"] == 0
    assert recorded[0][0] == "job"


def test_restore_check_rejects_an_incomplete_ledger_entry():
    try:
        reapply_deletions(
            [{"jobId": "job", "userId": "user", "completedAt": "now"}],
            lambda _user_id: False, lambda _user_id: None, lambda _row, _checked_at: None,
        )
    except ValueError as exc:
        assert "receiptHash" in str(exc)
    else:
        raise AssertionError("incomplete tombstone was accepted")
