from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app
from app.services.privacy import OWNED_TABLES, receipt_hash

MIGRATION = Path(__file__).resolve().parents[3] / "supabase" / "migrations" / "20261027011000_account_deletion_jobs.sql"


def test_deletion_receipts_are_hashed_and_jobs_survive_user_removal():
    sql = MIGRATION.read_text(encoding="utf-8").lower()
    assert "references auth.users" not in sql
    assert "enable row level security" in sql
    assert len(receipt_hash("opaque-deletion-receipt")) == 64


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
