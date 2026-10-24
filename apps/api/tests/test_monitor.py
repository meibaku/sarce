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
