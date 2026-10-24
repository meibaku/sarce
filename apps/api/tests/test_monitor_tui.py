"""The terminal monitor (scripts/monitor_tui.py): optional, so skipped where Textual isn't installed (CI)."""

import asyncio
import sys
from pathlib import Path

import pytest

pytest.importorskip("textual")
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import monitor_tui  # noqa: E402

ENGINE = {"engine": 0, "state": "searching", "game_id": "g1", "done": 10, "total": 40, "cpu": 12.0, "rss_mb": 150.0,
          "games_today": 3, "last_game_s": 90, "elapsedS": 30, "etaS": 90, "stale": False,
          "game": {"opponent": "rival", "opponent_rating": 900, "user_color": "white", "time_control": "600"}}
SNAP = {"at": "2026-10-24T12:00:00+00:00", "queue": {"pending": 5, "processing": 1, "complete": 4, "failed": 0, "total": 10},
        "perHour": 60, "etaHours": 0.1, "alerts": [{"kind": "stalled", "machine": "desk", "engine": 0, "stuckS": 200}],
        "machines": [{"machine": "desk", "role": "node", "online": True, "cpu": 50.0, "mem_used": 0.5, "mem_total_gb": 8,
                      "uptime_s": 100, "bundle": "abc", "rate": {"perHourNow": 60, "lastHour": 50}, "engineRows": [ENGINE]}]}
EVENTS = [{"at": "2026-10-24T12:00:00+00:00", "machine": "desk", "engine": 0, "kind": "claimed", "game_id": "g1", "detail": {}},
          {"at": "2026-10-24T11:59:00+00:00", "machine": "lap", "engine": None, "kind": "game_done", "game_id": "g0", "detail": {"seconds": 40}}]


class FakeApi:
    def get(self, path):
        if path.startswith("/monitor/snapshot"):
            return SNAP
        if path.startswith("/monitor/history"):
            return {"bucketMin": 10, "series": {"desk": {"a": 1, "b": 3}, "lap": {"b": 2}}}
        return {"events": EVENTS}


def test_helpers():
    assert monitor_tui.dur(None) == "–" and monitor_tui.dur(75) == "1m 15s" and monitor_tui.dur(3 * 86400) == "3.0d"
    assert monitor_tui.alert_text(SNAP["alerts"][0]) == "desk #0 no progress for 3m 20s"


def test_dashboard_renders_and_follows_the_selected_engine():
    async def run():
        app = monitor_tui.MonitorApp(FakeApi())
        async with app.run_test(size=(160, 45)) as pilot:
            await pilot.pause(0.5)
            assert app.query_one("#engines").row_count == 1
            assert [s.data for s in app.query("Sparkline")] == [[1.0, 3.0], [0.0, 2.0]]  # desk, then lap padded to desk's axis
            await pilot.press("tab")
            app.query_one("#engines").focus()
            await pilot.pause(0.2)
            assert app.selected == "desk:0"
            await pilot.press("escape", "m")
            assert app.selected is None and app.machine_filter == "desk"

    asyncio.run(run())


def test_startup_errors_show_and_dotted_hostnames_chart():
    class Down:
        def get(self, path):
            raise OSError("refused")

    async def run():
        app = monitor_tui.MonitorApp(Down())
        async with app.run_test(size=(160, 45)) as pilot:
            await pilot.pause(0.5)
            assert "refused" in str(app.query_one("#kpis").render())
            app._apply_slow({"bucketMin": 10, "series": {"worker.example.com": {"a": 1}}}, [])
            await pilot.pause(0.1)
            assert len(app.query("Sparkline")) == 1
            app._apply_slow({"bucketMin": 10, "series": {}}, [])
            await pilot.pause(0.1)
            assert len(app.query("Sparkline")) == 0

    asyncio.run(run())
