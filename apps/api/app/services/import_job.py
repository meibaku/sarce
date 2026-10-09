"""Background Chess.com import jobs with progress tracking."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from app.db.supabase import get_supabase
from app.services.analysis import AnalysisService
from app.services.chess_com import ChessComClient, normalize_chess_com_username
from app.services.game_store import GameStore

logger = logging.getLogger(__name__)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _progress_pct(archives_done: int, archives_total: int) -> float:
    if archives_total <= 0:
        return 0.0
    return round(min(100.0, (archives_done / archives_total) * 100), 1)


def _serialize_job(row: dict) -> dict:
    archives_total = int(row.get("archives_total") or 0)
    archives_done = int(row.get("archives_done") or 0)
    games_new = int(row.get("games_new") or 0)
    games_skipped = int(row.get("games_skipped") or 0)
    games_updated = int(row.get("games_updated") or 0)
    games_fetched = int(row.get("games_fetched") or 0)
    status = row.get("status") or "queued"

    if status == "complete":
        message = (
            f"Import complete: {games_new} new, {games_skipped} cached, "
            f"{games_updated} updated."
        )
    elif status == "failed":
        message = row.get("error_message") or "Import failed."
    elif archives_total > 0:
        message = (
            f"Importing archive {archives_done}/{archives_total} "
            f"({games_fetched} games scanned, {games_new} new, "
            f"{games_skipped} cached)."
        )
    else:
        message = "Preparing import..."

    return {
        "jobId": row["id"],
        "username": row.get("chess_com_username"),
        "status": status,
        "analyzeAfterImport": bool(row.get("analyze_after_import")),
        "archivesTotal": archives_total,
        "archivesDone": archives_done,
        "gamesFetched": games_fetched,
        "gamesNew": games_new,
        "gamesSkipped": games_skipped,
        "gamesUpdated": games_updated,
        "progressPct": _progress_pct(archives_done, archives_total),
        "message": message,
        "errorMessage": row.get("error_message"),
        "startedAt": row.get("started_at"),
        "finishedAt": row.get("finished_at"),
    }


class ImportJobService:
    def __init__(self) -> None:
        self.chess_com = ChessComClient()
        self.game_store = GameStore()
        self.analysis_service = AnalysisService()

    async def create_job(
        self,
        username: str,
        user_id: str,
        analyze: bool = True,
    ) -> dict:
        sb = get_supabase()
        res = (
            sb.table("import_jobs")
            .insert(
                {
                    "user_id": user_id,
                    "chess_com_username": username,
                    "status": "queued",
                    "analyze_after_import": analyze,
                }
            )
            .execute()
        )
        rows = res.data or []
        if not rows:
            raise RuntimeError("Failed to create import job")
        return _serialize_job(rows[0])

    async def get_job(self, job_id: str) -> dict | None:
        sb = get_supabase()
        res = (
            sb.table("import_jobs")
            .select("*")
            .eq("id", job_id)
            .limit(1)
            .execute()
        )
        rows = res.data or []
        if not rows:
            return None
        return _serialize_job(rows[0])

    async def get_active_job(
        self,
        user_id: str,
        username: str | None = None,
    ) -> dict | None:
        sb = get_supabase()
        query = (
            sb.table("import_jobs")
            .select("*")
            .eq("user_id", user_id)
            .in_("status", ["queued", "running"])
            .order("created_at", desc=True)
            .limit(1)
        )
        if username:
            query = query.eq(
                "chess_com_username",
                normalize_chess_com_username(username),
            )
        res = query.execute()
        rows = res.data or []
        if not rows:
            return None
        return _serialize_job(rows[0])

    async def _update_job(self, job_id: str, **fields) -> None:
        sb = get_supabase()
        sb.table("import_jobs").update(fields).eq("id", job_id).execute()

    async def run_job(self, job_id: str) -> None:
        sb = get_supabase()
        job_res = (
            sb.table("import_jobs")
            .select("*")
            .eq("id", job_id)
            .limit(1)
            .execute()
        )
        rows = job_res.data or []
        if not rows:
            return

        job = rows[0]
        username = job["chess_com_username"]
        user_id = job["user_id"]
        analyze = bool(job.get("analyze_after_import"))

        await self._update_job(
            job_id,
            status="running",
            started_at=_utc_now(),
            error_message=None,
        )

        games_fetched = 0
        games_new = 0
        games_skipped = 0
        games_updated = 0

        try:
            archives = await self.chess_com.fetch_recent_archives(
                username,
                limit=None,
            )
            await self._update_job(job_id, archives_total=len(archives))

            for index, archive_url in enumerate(archives, start=1):
                batch = await self.chess_com.fetch_games_from_archive(archive_url)
                for raw in batch:
                    games_fetched += 1
                    outcome = await self.game_store.upsert_imported_game(
                        raw,
                        username,
                        user_id,
                    )
                    if outcome == "new":
                        games_new += 1
                    elif outcome == "skipped":
                        games_skipped += 1
                    elif outcome == "updated":
                        games_updated += 1

                await self._update_job(
                    job_id,
                    archives_done=index,
                    games_fetched=games_fetched,
                    games_new=games_new,
                    games_skipped=games_skipped,
                    games_updated=games_updated,
                )

            if analyze and games_new > 0:
                await self.analysis_service.analyze_pending(
                    user_id=user_id,
                    chess_com_username=username,
                )

            await self._update_job(
                job_id,
                status="complete",
                finished_at=_utc_now(),
                games_fetched=games_fetched,
                games_new=games_new,
                games_skipped=games_skipped,
                games_updated=games_updated,
            )
        except Exception as exc:
            logger.exception("Import job %s failed: %s", job_id, exc)
            await self._update_job(
                job_id,
                status="failed",
                finished_at=_utc_now(),
                error_message=str(exc),
                games_fetched=games_fetched,
                games_new=games_new,
                games_skipped=games_skipped,
                games_updated=games_updated,
            )
