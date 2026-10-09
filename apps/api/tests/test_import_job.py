from unittest.mock import AsyncMock, patch

import pytest

from app.services.import_job import ImportJobService, _progress_pct, _serialize_job


def test_progress_pct():
    assert _progress_pct(0, 10) == 0.0
    assert _progress_pct(5, 10) == 50.0
    assert _progress_pct(10, 10) == 100.0


def test_serialize_job_complete_message():
    payload = _serialize_job(
        {
            "id": "job-1",
            "chess_com_username": "dratius",
            "status": "complete",
            "archives_total": 4,
            "archives_done": 4,
            "games_fetched": 100,
            "games_new": 12,
            "games_skipped": 88,
            "games_updated": 0,
            "analyze_after_import": True,
        }
    )

    assert payload["status"] == "complete"
    assert payload["progressPct"] == 100.0
    assert "12 new" in payload["message"]
    assert "88 cached" in payload["message"]


class TestImportJobService:
    @pytest.mark.asyncio
    @patch("app.services.import_job.get_supabase")
    async def test_create_job(self, mock_get_supabase):
        class FakeResult:
            def __init__(self, data):
                self.data = data

        class FakeQuery:
            def insert(self, row):
                self.row = row
                return self

            def execute(self):
                return FakeResult(
                    [
                        {
                            "id": "job-1",
                            **self.row,
                            "archives_total": 0,
                            "archives_done": 0,
                            "games_fetched": 0,
                            "games_new": 0,
                            "games_skipped": 0,
                            "games_updated": 0,
                        }
                    ]
                )

        mock_get_supabase.return_value.table.return_value = FakeQuery()
        service = ImportJobService()

        job = await service.create_job("dratius", "user-1", analyze=True)

        assert job["jobId"] == "job-1"
        assert job["username"] == "dratius"
        assert job["status"] == "queued"

    @pytest.mark.asyncio
    @patch("app.services.import_job.ImportJobService._update_job", new_callable=AsyncMock)
    @patch("app.services.import_job.get_supabase")
    async def test_run_job_counts_new_and_skipped(
        self,
        mock_get_supabase,
        mock_update_job,
    ):
        class FakeResult:
            def __init__(self, data):
                self.data = data

        class FakeQuery:
            def __init__(self):
                self.filters = {}

            def select(self, *_args):
                return self

            def eq(self, key, value):
                self.filters[key] = value
                return self

            def limit(self, *_args):
                return self

            def execute(self):
                return FakeResult(
                    [
                        {
                            "id": "job-1",
                            "chess_com_username": "dratius",
                            "user_id": "user-1",
                            "analyze_after_import": False,
                        }
                    ]
                )

        mock_get_supabase.return_value.table.return_value = FakeQuery()
        service = ImportJobService()
        service.chess_com.fetch_recent_archives = AsyncMock(
            return_value=["https://archive/1"]
        )
        service.chess_com.fetch_games_from_archive = AsyncMock(
            return_value=[{"url": "g1"}, {"url": "g2"}]
        )
        service.game_store.upsert_imported_game = AsyncMock(
            side_effect=["new", "skipped"]
        )

        await service.run_job("job-1")

        final_update = mock_update_job.await_args_list[-1].kwargs
        assert final_update["status"] == "complete"
        assert final_update["games_new"] == 1
        assert final_update["games_skipped"] == 1
        assert final_update["games_fetched"] == 2
