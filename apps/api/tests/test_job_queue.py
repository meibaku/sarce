"""Per-user analysis job queue — Chaos Lens M8. The queue is faked; no database."""

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import BackgroundTasks
from fastapi.testclient import TestClient

from app.config import settings
from app.main import app
from app.services import job_queue
from app.services.job_queue import analysis_handlers, queue_analysis, run_one

client = TestClient(app)
MIGRATION = Path(__file__).resolve().parents[3] / "supabase" / "migrations" / "20261010007000_analysis_jobs.sql"


class FakeQueue:
    def __init__(self, jobs):
        self.jobs = list(jobs)
        self.finished = []

    def claim(self):
        return self.jobs.pop(0) if self.jobs else None

    def finish(self, job_id, error=None, retry=False):
        self.finished.append((job_id, error, retry))


def job(job_id="j1", attempts=1, kind="analyze_pending", **extra):
    return {"id": job_id, "kind": kind, "attempts": attempts, "user_id": "u1",
            "chess_com_username": "tal_fan", "payload": {"limit": 5}, **extra}


class TestRunOne:
    def test_empty_queue(self):
        assert asyncio.run(run_one(FakeQueue([]), {})) is False

    def test_runs_the_handler_and_marks_the_job_done(self):
        analyze = AsyncMock()
        queue = FakeQueue([job()])
        assert asyncio.run(run_one(queue, analysis_handlers(analyze))) is True
        analyze.assert_awaited_once_with(user_id="u1", chess_com_username="tal_fan", limit=5)
        assert queue.finished == [("j1", None, False)]

    def test_failure_is_retried_until_the_attempt_limit(self):
        failing = {"analyze_pending": AsyncMock(side_effect=RuntimeError("engine died"))}
        first, last = FakeQueue([job(attempts=1)]), FakeQueue([job(attempts=3)])
        asyncio.run(run_one(first, failing))
        asyncio.run(run_one(last, failing))
        assert first.finished == [("j1", "engine died", True)]
        assert last.finished == [("j1", "engine died", False)]

    def test_unknown_kind_fails_without_retry(self):
        queue = FakeQueue([job(kind="mystery")])
        asyncio.run(run_one(queue, {}))
        (job_id, error, retry), = queue.finished
        assert job_id == "j1" and "mystery" in error and retry is False


class TestQueueAnalysis:
    def test_disabled_uses_background_tasks_as_before(self, monkeypatch):
        monkeypatch.setattr(settings, "job_queue_enabled", False)
        tasks, analyze = BackgroundTasks(), AsyncMock()
        with patch.object(job_queue.JobQueue, "enqueue") as enqueue:
            queue_analysis(tasks, analyze, user_id="u1", username="tal_fan", limit=3)
        enqueue.assert_not_called()
        assert len(tasks.tasks) == 1
        assert tasks.tasks[0].kwargs == {"user_id": "u1", "chess_com_username": "tal_fan", "limit": 3}

    def test_enabled_enqueues_a_durable_job(self, monkeypatch):
        monkeypatch.setattr(settings, "job_queue_enabled", True)
        tasks = BackgroundTasks()
        with patch.object(job_queue.JobQueue, "enqueue") as enqueue:
            queue_analysis(tasks, AsyncMock(), user_id="u1", username="tal_fan", limit=None)
        enqueue.assert_called_once_with("analyze_pending", "u1", "tal_fan", {"limit": None})
        assert tasks.tasks == []


class TestRoutes:
    def test_jobs_endpoint_is_empty_when_the_queue_is_off(self, monkeypatch):
        monkeypatch.setattr(settings, "job_queue_enabled", False)
        assert client.get("/games/jobs").json() == {"jobs": []}

    def test_jobs_endpoint_lists_the_callers_jobs(self, monkeypatch):
        monkeypatch.setattr(settings, "job_queue_enabled", True)
        with patch.object(job_queue.JobQueue, "recent", return_value=[{"id": "j1"}]) as recent:
            assert client.get("/games/jobs?user_id=u-1").json() == {"jobs": [{"id": "j1"}]}
        recent.assert_called_once_with("u-1")

    @patch("app.routers.games.queue_analysis")
    def test_analyze_goes_through_the_queue_helper(self, mock_queue):
        res = client.post("/games/analyze", json={"username": " Tal_Fan ", "limit": 4})
        assert res.status_code == 200
        assert mock_queue.call_args.kwargs == {"user_id": None, "username": "tal_fan", "limit": 4}


class TestMigration:
    def test_claim_function_is_atomic_and_service_only(self):
        sql = MIGRATION.read_text(encoding="utf-8")
        assert "alter table public.analysis_jobs enable row level security" in sql
        assert "for update skip locked" in sql
        assert "is not distinct from j.user_id" in sql
        assert "revoke all on function public.claim_next_analysis_job() from public, anon, authenticated" in sql
