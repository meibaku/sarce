from pathlib import Path

from app.config import Settings
from app.services.readiness import readiness_checks


def pilot_settings(engine: Path) -> Settings:
    return Settings(
        pilot_mode="style_v1",
        auth_required=True,
        job_queue_enabled=True,
        human_model="maia2",
        stockfish_path=str(engine),
        supabase_url="https://example.supabase.co",
        supabase_service_role_key="secret",
        pilot_operators=["operator"],
        pilot_backup_retention_days=30,
    )


def test_ready_requires_every_pilot_dependency(tmp_path):
    engine = tmp_path / "stockfish"
    engine.write_text("test", encoding="utf-8")
    assert all(readiness_checks(pilot_settings(engine), lambda: None).values())


def test_database_failure_is_not_ready(tmp_path):
    engine = tmp_path / "stockfish"
    engine.write_text("test", encoding="utf-8")

    def unavailable():
        raise RuntimeError("offline")

    assert readiness_checks(pilot_settings(engine), unavailable)["database"] is False


def test_local_defaults_are_not_pilot_ready():
    checks = readiness_checks(Settings(), lambda: None)
    assert checks["pilot_mode"] is False
    assert checks["authentication"] is False
    assert checks["durable_queue"] is False
    assert checks["backup_retention"] is False


def test_backup_retention_must_be_in_the_approved_range(tmp_path):
    engine = tmp_path / "stockfish"
    engine.write_text("test", encoding="utf-8")
    assert readiness_checks(
        pilot_settings(engine).model_copy(update={"pilot_backup_retention_days": 0}), lambda: None
    )["backup_retention"] is False
    assert readiness_checks(
        pilot_settings(engine).model_copy(update={"pilot_backup_retention_days": 91}), lambda: None
    )["backup_retention"] is False
