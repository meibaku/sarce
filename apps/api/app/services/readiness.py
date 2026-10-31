from __future__ import annotations

from pathlib import Path
import json

from app.config import Settings


MIN_BACKUP_RETENTION_DAYS = 1
MAX_BACKUP_RETENTION_DAYS = 90


def restore_check_passed(path: str) -> bool:
    if not path or not Path(path).is_file():
        return False
    try:
        result = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False
    return result.get("status") == "passed" and result.get("remaining") == 0 and bool(result.get("checkedAt"))


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
        "restore_deletion_check": restore_check_passed(config.pilot_restore_check_path),
    }
    if checks["supabase_configured"]:
        try:
            database_probe()
            checks["database"] = True
        except Exception:
            checks["database"] = False
    else:
        checks["database"] = False
    return checks
