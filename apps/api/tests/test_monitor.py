"""Analysis monitor (app/services/monitor.py, procstats.py, the gateway's report)."""

import os
import sys
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from app.node_gateway import split_node
from app.services import monitor
from app.services.procstats import Sampler


def test_slots_are_reused_and_progress_counts_each_position_once():
    with patch("app.services.monitor.get_supabase", return_value=MagicMock()):
        with monitor.track_game("g1") as a, monitor.track_game("g2") as b:
            assert (a.slot, b.slot) == (0, 1)
            a.phase("searching", total=10)
            store = monitor.CountingStore(SimpleNamespace(get=lambda k, n: None, put=lambda r: None))
            token = monitor.current.set(a)
            for key in ("k1", "k1", "k2"):
                store.get(key, 100)
            monitor.current.reset(token)
            assert a.done == 2 and a.total == 10
        with monitor.track_game("g3") as c:
            assert c.slot == 0  # freed slots come back


def test_split_node_names():
    assert split_node("desktop-fuer0cc-2") == ("desktop-fuer0cc", 2)
    assert split_node("solo") == ("solo", None)


def test_node_report_logs_a_restart_only_when_the_process_start_changes():
    sb = MagicMock()
    started = 1_800_000_000.0
    known = monitor._iso(started)
    sb.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = [{"process_started_at": known}]
    with patch("app.services.monitor.get_supabase", return_value=sb), patch("app.services.monitor.event") as ev:
        monitor.node_report("desk", {"cpu": 50}, [{"engine": 0, "state": "searching", "done": 3, "total": 40}], "abc", started)
        assert not ev.called
        monitor.node_report("desk", {"cpu": 50}, [], "abc", started + 600)
        assert ev.call_args.args[0] == "node_started"


def test_alerts_flag_offline_machines_stalls_and_rate_drops():
    t = monitor.now()
    old = (t - timedelta(minutes=5)).isoformat()
    fresh = t.isoformat()
    tables = {
        "machine_snapshots": [{"machine": "desk", "updated_at": old}, {"machine": "lap", "updated_at": fresh}],
        "engine_snapshots": [{"machine": "lap", "engine": 1, "state": "searching", "progress_at": old, "updated_at": fresh}],
        "analysis_throughput": [{"minute": (t - timedelta(minutes=20)).isoformat(), "machine": "lap", "games": 30}],
    }

    class Q:
        def __init__(self, name):
            self.name = name

        def __getattr__(self, attr):
            return lambda *a, **k: self

        def execute(self):
            return SimpleNamespace(data=tables[self.name])

    sb = MagicMock()
    sb.table.side_effect = Q
    with patch("app.services.monitor.get_supabase", return_value=sb):
        found = monitor.alerts()
    assert "offline|desk" in found and "stalled-1|lap" in found and "drop|lap" in found
    assert found["drop|lap"][2]["perHourNow"] == 0


@pytest.mark.skipif(sys.platform != "win32", reason="Windows counters")
def test_sampler_reads_this_process():
    s = Sampler()
    s.process(os.getpid())
    sum(range(200_000))
    cpu, rss = s.process(os.getpid())
    assert cpu is not None and rss and rss > 1
    assert s.machine()["memTotalGb"] > 0


def test_engine_searches_count_and_done_counts_once():
    from app.services import nodes

    with patch("app.services.monitor.get_supabase", return_value=MagicMock()):
        with monitor.track_game("g9") as t:
            t.phase("searching", total=5)
            engine = monitor.CountingEngine(SimpleNamespace(engine_version="sf", analyse=lambda b, nodes, multipv: []))
            import chess

            token = monitor.current.set(t)
            engine.analyse(chess.Board(), nodes=1, multipv=1)
            monitor.current.reset(token)
            assert t.done == 1
    sb = MagicMock()
    sb.table.return_value.update.return_value.eq.return_value.eq.return_value.is_.return_value.execute.side_effect = [
        SimpleNamespace(data=[{"game_id": "g"}]), SimpleNamespace(data=[]),
    ]
    with patch("app.services.nodes.get_supabase", return_value=sb):
        assert nodes.NodeService().done("g", "desk-0") is True
        assert nodes.NodeService().done("g", "desk-0") is False


@pytest.mark.skipif(sys.platform != "win32", reason="Windows counters")
def test_uptime_is_unsigned():
    from app.services.procstats import uptime_s

    assert uptime_s() > 0


def test_gateway_refuses_a_malformed_report():
    from fastapi.testclient import TestClient

    from app.node_gateway import app
    from app.services import nodes

    with patch.object(nodes.settings, "node_token", "s3cret"), patch("app.services.monitor.node_report") as rep:
        client = TestClient(app)
        bad = client.post("/nodes/report", headers={"X-Sarce-Node": "s3cret"}, json={"node": "desk", "engines": [{}]})
        assert bad.status_code == 422 and not rep.called
        ok = client.post("/nodes/report", headers={"X-Sarce-Node": "s3cret"}, json={"node": "desk", "engines": [{"engine": 0, "state": "searching", "extra": 1}]})
        assert ok.status_code == 200 and rep.call_args.args[2][0]["engine"] == 0


def test_monitor_routes_and_the_stream():
    from fastapi.testclient import TestClient

    from app.main import app

    client = TestClient(app)
    snap = {"at": "t", "queue": {"pending": 1}, "machines": [], "alerts": []}
    with patch("app.services.monitor.snapshot", return_value=snap):
        assert client.get("/monitor/snapshot").json()["queue"]["pending"] == 1
    with patch("app.services.monitor.events", return_value=[{"id": 1, "kind": "claimed"}]):
        assert client.get("/monitor/events?limit=5").json()["events"][0]["kind"] == "claimed"


def test_node_times_are_placed_on_the_servers_clock():
    sb = MagicMock()
    sb.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = []
    with patch("app.services.monitor.get_supabase", return_value=sb), patch("app.services.monitor.event"):
        monitor.node_report("desk", {}, [{"engine": 0, "state": "searching", "startedAgo": 90, "progressAgo": 5}], "b", None)
    row = sb.table.return_value.upsert.call_args_list[-1].args[0][0]
    from datetime import datetime

    started = datetime.fromisoformat(row["started_at"])
    assert 85 <= (monitor.now() - started).total_seconds() <= 95


def test_only_operators_read_the_monitor_when_signed_in():
    from fastapi.testclient import TestClient

    from app import deps
    from app.main import app
    from app.routers import monitor as monitor_router

    client = TestClient(app)
    snap = {"at": "t", "queue": {}, "machines": [], "alerts": []}
    user = SimpleNamespace(user=SimpleNamespace(id="u-1"))
    sb = MagicMock()
    sb.auth.get_user.return_value = user
    signed_in = {"Authorization": "Bearer tok"}
    with patch.object(deps, "get_supabase", return_value=sb), patch("app.services.monitor.snapshot", return_value=snap):
        with patch.object(monitor_router.settings, "monitor_operators", []):
            assert client.get("/monitor/snapshot", headers=signed_in).status_code == 403
            assert client.get("/monitor/snapshot").status_code == 200  # local-first: the machine's owner
        with patch.object(monitor_router.settings, "monitor_operators", ["u-1"]):
            assert client.get("/monitor/snapshot", headers=signed_in).status_code == 200


def test_history_fills_quiet_buckets_with_zero():
    t = monitor.now().replace(second=0, microsecond=0)
    t = t - timedelta(minutes=t.minute % 10)
    rows = [{"minute": (t - timedelta(minutes=40)).isoformat(), "machine": "desk", "games": 3}, {"minute": t.isoformat(), "machine": "desk", "games": 2}]
    sb = MagicMock()
    sb.table.return_value.select.return_value.gt.return_value.order.return_value.range.return_value.execute.return_value = SimpleNamespace(data=rows)
    sb.table.return_value.select.return_value.gt.return_value.in_.return_value.order.return_value.execute.return_value = SimpleNamespace(data=[])
    with patch("app.services.monitor.get_supabase", return_value=sb):
        series = monitor.history(1, 10)["series"]["desk"]
    assert list(series.values()) == [3, 0, 0, 0, 2]


def test_a_game_already_processing_is_left_alone():
    import asyncio

    from app.services.analysis import AnalysisService

    sb = MagicMock()
    sb.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = SimpleNamespace(
        data={"id": "g", "pgn": '[Event "x"]\n\n1. e4 e5 *', "user_color": "white", "analysis_status": "processing"}
    )
    with patch("app.services.analysis.get_supabase", return_value=sb), patch.object(AnalysisService, "_classify") as classify:
        assert asyncio.run(AnalysisService()._analyze_game("g")) is None
    assert not classify.called and not sb.table.return_value.update.called


def test_server_events_carry_their_slot_and_stalls_their_engine():
    with patch("app.services.monitor.searched_by_node", return_value=False), patch("app.services.monitor.bump"), \
            patch("app.services.monitor.event") as ev:
        monitor.game_finished("g", 30, 40, 20, 3)
    assert ev.call_args.kwargs["engine"] == 3
    with patch("app.services.monitor.get_supabase", return_value=MagicMock()), patch("app.services.monitor._sampler") as sampler, \
            patch("app.services.monitor.event") as ev, patch("app.services.monitor.alerts") as alerts:
        sampler.machine.return_value = {"cpu": 1, "memUsed": 0.1, "memTotalGb": 8, "uptimeS": 1}
        monitor._active_alerts.clear()
        alerts.return_value = {"stalled-2|desk": ("stalled", "desk", {"engine": 2, "stuckS": 200})}
        monitor.tick(1)
        assert ev.call_args.kwargs == {"machine": "desk", "engine": 2, "stuckS": 200}
        alerts.return_value = {}
        monitor.tick(1)
        assert ev.call_args.args == ("recovered",) and ev.call_args.kwargs == {"machine": "desk", "engine": 2, "cleared": "stalled"}


def test_the_server_can_set_node_engines():
    from app.services import nodes

    nodes.bundle.cache_clear()  # the version is computed once per process (settings don't change while it runs)
    with patch.object(nodes.settings, "node_workers", 0):
        before = nodes.NodeService().config()
    nodes.bundle.cache_clear()
    assert before["workers"] is None
    with patch.object(nodes.settings, "node_workers", 7):
        after = nodes.NodeService().config()
    nodes.bundle.cache_clear()
    assert after["workers"] == 7 and after["version"] != before["version"]  # nodes restart with the new count
