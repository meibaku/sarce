from pathlib import Path
import json

from app.config import Settings
from app.services.readiness import readiness_checks


def pilot_settings(engine: Path) -> Settings:
    restore_result = engine.parent / "restore-deletion-check.json"
    restore_result.write_text(json.dumps({"status": "passed", "remaining": 0, "checkedAt": "2026-10-29T00:00:00Z"}), encoding="utf-8")
    artifact_sha = "a" * 40
    runtime_manifest = engine.parent / "runtime-manifest.json"
    runtime_manifest.write_text(json.dumps({
        "schemaVersion": 1, "status": "passed", "artifactSha": artifact_sha,
        "checkedAt": "2026-10-29T00:00:00Z", "stockfishVersion": "19",
        "maiaVersion": "0.11.0",
        "maiaCheckpoints": {"blitz": {"normalized": True}, "rapid": {"normalized": True}},
        "brilliantV4": {"soundEpLoss": 0.03, "lostEp": 0.1, "alternativeEp": 0.1, "findRateMax": 0.2},
    }), encoding="utf-8")
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
        pilot_restore_check_path=str(restore_result),
        pilot_artifact_sha=artifact_sha,
        pilot_runtime_manifest_path=str(runtime_manifest),
        analysis_workers=2,
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
    assert checks["restore_deletion_check"] is False
    assert checks["artifact_identity"] is False


def test_backup_retention_must_be_in_the_approved_range(tmp_path):
    engine = tmp_path / "stockfish"
    engine.write_text("test", encoding="utf-8")
    assert readiness_checks(
        pilot_settings(engine).model_copy(update={"pilot_backup_retention_days": 0}), lambda: None
    )["backup_retention"] is False


def test_restore_deletion_check_must_be_a_passing_result(tmp_path):
    engine = tmp_path / "stockfish"
    engine.write_text("test", encoding="utf-8")
    failed = tmp_path / "failed.json"
    failed.write_text(json.dumps({"status": "failed", "remaining": 1, "checkedAt": "now"}), encoding="utf-8")
    assert readiness_checks(
        pilot_settings(engine).model_copy(update={"pilot_restore_check_path": str(failed)}), lambda: None
    )["restore_deletion_check"] is False
    assert readiness_checks(
        pilot_settings(engine).model_copy(update={"pilot_backup_retention_days": 91}), lambda: None
    )["backup_retention"] is False


def test_runtime_identity_mismatch_is_not_ready(tmp_path):
    engine = tmp_path / "stockfish"
    engine.write_text("test", encoding="utf-8")
    config = pilot_settings(engine).model_copy(update={"pilot_artifact_sha": "b" * 40})
    checks = readiness_checks(config, lambda: None)
    assert checks["artifact_identity"] is False
    assert checks["runtime_manifest"] is True
