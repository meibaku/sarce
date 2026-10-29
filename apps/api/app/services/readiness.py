from __future__ import annotations

from pathlib import Path

from app.config import Settings


MIN_BACKUP_RETENTION_DAYS = 1
MAX_BACKUP_RETENTION_DAYS = 90


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
