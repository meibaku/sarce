"""
Per-user analysis job queue — Chaos Lens M8 (docs/CHAOS_PLAN.md).

A Postgres table plus one polling worker inside the API process: no Redis or Celery.
Off by default (`JOB_QUEUE_ENABLED`); when off, analysis keeps using FastAPI
BackgroundTasks exactly as in Phase 1.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Awaitable, Callable

from fastapi import BackgroundTasks

from app.config import settings
from app.db.supabase import get_supabase

logger = logging.getLogger(__name__)

TABLE = "analysis_jobs"
MAX_ATTEMPTS = 3
Handler = Callable[[dict], Awaitable[None]]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class JobQueue:
    """Supabase-backed queue operations."""

    def enqueue(self, kind: str, user_id: str | None, username: str | None, payload: dict) -> dict:
        row = {"kind": kind, "user_id": user_id, "chess_com_username": username, "payload": payload}
        return get_supabase().table(TABLE).insert(row).execute().data[0]

    def claim(self) -> dict | None:
        """Atomically take the next job whose owner has nothing running (see the migration)."""
        res = get_supabase().rpc("claim_next_analysis_job", {}).execute()
        return res.data[0] if res.data else None

    def finish(self, job_id: str, error: str | None = None, retry: bool = False) -> None:
        status = "queued" if retry else ("failed" if error else "done")
        update = {"status": status, "error": error}
        if not retry:
            update["finished_at"] = _now()
        get_supabase().table(TABLE).update(update).eq("id", job_id).execute()

    def requeue_stale(self, older_than_minutes: int) -> int:
        """Jobs left `running` by a crashed worker go back to the queue."""
        cutoff = (datetime.now(timezone.utc) - timedelta(minutes=older_than_minutes)).isoformat()
        res = (
            get_supabase()
            .table(TABLE)
            .update({"status": "queued"})
            .eq("status", "running")
            .lt("started_at", cutoff)
            .execute()
        )
        return len(res.data or [])

    def recent(self, user_id: str, limit: int = 20) -> list[dict]:
        res = (
            get_supabase()
            .table(TABLE)
            .select("id, kind, status, attempts, error, created_at, started_at, finished_at")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        return res.data or []


async def run_one(queue: JobQueue, handlers: dict[str, Handler]) -> bool:
    """Claim and run a single job. Returns False when the queue had nothing to give."""
    job = await asyncio.to_thread(queue.claim)
    if job is None:
        return False
    handler = handlers.get(job["kind"])
    try:
        if handler is None:
            raise ValueError(f"No handler for job kind {job['kind']!r}")
        await handler(job)
    except Exception as exc:  # the worker must outlive any one job
        logger.exception("Job %s failed", job["id"])
        retry = handler is not None and job.get("attempts", 1) < MAX_ATTEMPTS
        await asyncio.to_thread(queue.finish, job["id"], str(exc)[:500], retry)
    else:
        await asyncio.to_thread(queue.finish, job["id"])
    return True


async def worker_loop(queue: JobQueue, handlers: dict[str, Handler], poll_seconds: float) -> None:
    """Run jobs until cancelled; sleeps only when the queue is empty."""
    try:
        await asyncio.to_thread(queue.requeue_stale, settings.job_stale_minutes)
    except Exception:
        logger.exception("Could not requeue stale jobs")
    while True:
        try:
            worked = await run_one(queue, handlers)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Job worker error")
            worked = False
        if not worked:
            await asyncio.sleep(poll_seconds)


def queue_analysis(
    background_tasks: BackgroundTasks,
    analyze_pending: Callable[..., Awaitable[object]],
    *,
    user_id: str | None,
    username: str | None,
    limit: int | None,
) -> None:
    """Queue "analyse this user's pending games": a durable job when enabled, else a BackgroundTask."""
    if settings.job_queue_enabled:
        JobQueue().enqueue("analyze_pending", user_id, username, {"limit": limit})
        return
    background_tasks.add_task(
        analyze_pending, user_id=user_id, chess_com_username=username, limit=limit
    )


def analysis_handlers(analyze_pending: Callable[..., Awaitable[object]]) -> dict[str, Handler]:
    async def handle_analyze_pending(job: dict) -> None:
        await analyze_pending(
            user_id=job.get("user_id"),
            chess_com_username=job.get("chess_com_username"),
            limit=(job.get("payload") or {}).get("limit"),
        )

    return {"analyze_pending": handle_analyze_pending}
