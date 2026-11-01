from __future__ import annotations

from pathlib import Path
import json

from app.config import Settings
from app.services.runtime_identity import runtime_identity_checks


MIN_BACKUP_RETENTION_DAYS = 1
MAX_BACKUP_RETENTION_DAYS = 90


def restore_check_passed(path: str, artifact_sha: str = "", image_digest: str = "") -> bool:
    if not path or not Path(path).is_file():
        return False
    try:
        result = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False
    return (
        result.get("status") == "passed"
        and result.get("remaining") == 0
        and bool(result.get("checkedAt"))
        and result.get("artifactSha") == artifact_sha
        and result.get("imageDigest") == image_digest
        and bool(result.get("checks"))
        and all(result["checks"].values())
    )


def readiness_checks(config: Settings, database_probe) -> dict[str, bool]:
    """Return fail-closed pilot prerequisites without loading the large Maia model."""
    checks = {
        "pilot_mode": config.pilot_mode == "style_v1",
        "authentication": config.auth_required,
        "durable_queue": config.job_queue_enabled,
        "human_model": config.human_model == "maia2",
        "stockfish": Path(config.stockfish_executable).is_file(),
        "supabase_configured": bool(config.supabase_url and config.supabase_service_role_key),
        "pilot_operator": bool(config.pilot_operators),
        "backup_retention": (
            config.pilot_backup_retention_days is not None
            and MIN_BACKUP_RETENTION_DAYS
            <= config.pilot_backup_retention_days
            <= MAX_BACKUP_RETENTION_DAYS
        ),
        "restore_deletion_check": restore_check_passed(
            config.pilot_restore_check_path, config.pilot_artifact_sha, config.pilot_image_digest
        ),
        "backup_retention_30_days": config.pilot_backup_retention_days == 30,
        "analysis_workers": config.analysis_workers == 2,
        "experimental_lenses_disabled": not config.position_evals_enabled,
    }
    checks.update(runtime_identity_checks(config))
    if checks["supabase_configured"]:
        try:
            database_probe()
            checks["database"] = True
        except Exception:
            checks["database"] = False
    else:
        checks["database"] = False
    return checks
