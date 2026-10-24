"""Paired Sarce Nodes (app/services/nodes.py, app/node_gateway.py, ADR 0010)."""

import io
import zipfile
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from app.node_gateway import app
from app.services import nodes


def test_token_check_needs_a_configured_token():
    with patch.object(nodes.settings, "node_token", ""):
        assert not nodes.token_ok("anything")
    with patch.object(nodes.settings, "node_token", "s3cret"):
        assert nodes.token_ok("s3cret") and not nodes.token_ok("wrong") and not nodes.token_ok(None)


def test_gateway_refuses_unpaired_callers():
    client = TestClient(app)
    with patch.object(nodes.settings, "node_token", "s3cret"):
        assert client.get("/nodes/config").status_code == 401
        assert client.get("/nodes/config", headers={"X-Sarce-Node": "nope"}).status_code == 401
        ok = client.get("/nodes/config", headers={"X-Sarce-Node": "s3cret"})
        assert ok.status_code == 200 and ok.json()["settings"]["ANALYSIS_NODES"] == str(nodes.settings.analysis_nodes)


def test_bundle_has_the_server_code_the_node_and_a_stable_version():
    data, version = nodes.bundle()
    names = zipfile.ZipFile(io.BytesIO(data)).namelist()
    assert "api/app/services/position_evals.py" in names and "node/sarce_node.py" in names and "node/install.ps1" in names
    assert zipfile.ZipFile(io.BytesIO(data)).read("VERSION").decode() == version and len(version) == 12
    nodes.bundle.cache_clear()
    assert nodes.bundle()[1] == version


def test_position_keys_cover_every_mainline_position():
    keys = nodes.position_keys('[Event "?"]\n\n1. e4 e5 2. Nf3 *')
    assert len(keys) == 4 and keys[0].startswith("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq -")


def test_put_rows_refuses_rows_at_other_node_counts():
    sb = MagicMock()
    sb.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value.data = [{"positions": 3}]
    good = {"fen_key": "k1", "nodes": nodes.settings.analysis_nodes, "lines": [], "multipv": 4}
    bad = {"fen_key": "k2", "nodes": 10, "lines": []}
    with patch("app.services.nodes.get_supabase", return_value=sb):
        stored = nodes.NodeService().put_rows("g1", "desk-0", [good, bad], [{"fen_key": "k3", "nodes": nodes.THREAT_NODES, "threat_uci": "e7e5"}])
    assert stored == 2
    upserted = [c.args[0] for c in sb.table.return_value.upsert.call_args_list]
    assert upserted[0] == [good] and upserted[1][0]["fen_key"] == "k3"


def test_server_analysis_skips_games_a_node_is_searching():
    import asyncio

    from app.services.analysis import AnalysisService

    sb = MagicMock()
    sb.table.return_value.select.return_value.eq.return_value.order.return_value.limit.return_value.not_.in_.return_value.execute.return_value.data = [{"id": "b"}]
    service = AnalysisService()
    seen = []

    async def fake_analyze(game_id):
        seen.append(game_id)
        return {"gameId": game_id}

    with patch("app.services.analysis.get_supabase", return_value=sb), patch("app.services.nodes.live_leases", return_value={"a"}), patch.object(service, "analyze_game", side_effect=fake_analyze):
        asyncio.run(service.analyze_pending(limit=2))
    assert "a" not in seen


def test_claim_waits_when_the_server_ignores_the_cache_and_uses_the_atomic_rpc():
    with patch.object(nodes.settings, "position_evals_enabled", False):
        assert nodes.NodeService().claim("desk-0") is None
    sb = MagicMock()
    sb.rpc.return_value.execute.return_value.data = None
    with patch.object(nodes.settings, "position_evals_enabled", True), patch("app.services.nodes.get_supabase", return_value=sb):
        assert nodes.NodeService().claim("desk-0") is None
    sb.rpc.assert_called_once_with("claim_node_game", {"p_node": "desk-0", "p_lease_s": nodes.LEASE_S})


def test_bundle_signature_and_settings_in_the_version():
    import hashlib
    import hmac as h

    data, version = nodes.bundle()
    with patch.object(nodes.settings, "node_token", "s3cret"):
        assert nodes.signature(data) == h.new(b"s3cret", data, hashlib.sha256).hexdigest()
    nodes.bundle.cache_clear()
    with patch.object(nodes.settings, "analysis_nodes", 2_000_000):
        assert nodes.bundle()[1] != version  # a settings change is a new version: nodes restart with it
    nodes.bundle.cache_clear()


def test_status_groups_engines_by_machine_and_splits_one_event():
    from datetime import timedelta
    from types import SimpleNamespace

    now = nodes.now()
    recent = (now - timedelta(minutes=5)).isoformat()
    leases = [
        {"game_id": "g1", "node": "desk-0", "done_at": recent, "heartbeat_at": recent, "positions": 40},
        {"game_id": "g2", "node": "desk-1", "done_at": None, "heartbeat_at": now.isoformat(), "positions": 10},
        {"game_id": "g3", "node": "desk-2", "done_at": recent, "heartbeat_at": recent, "positions": 30},
    ]
    counts = {"pending": 100, "processing": 1, "complete": 900, "failed": 0}
    analysed = [{"id": f"x{i}"} for i in range(18)] + [{"id": "g1"}, {"id": "g3"}]

    class Q:
        def __init__(self, table):
            self.table, self.filters = table, {}

        def select(self, *a, **k):
            return self

        def eq(self, col, val):
            self.filters[col] = val
            return self

        def gt(self, col, val):
            self.filters["gt"] = col
            return self

        def order(self, *a, **k):
            return self

        def range(self, a, b):
            return self

        def limit(self, n):
            return self

        def execute(self):
            if self.table == "node_leases":
                return SimpleNamespace(data=leases, count=None)
            if self.filters.get("gt") == "analysed_at":
                return SimpleNamespace(data=analysed, count=None)
            return SimpleNamespace(data=[], count=counts[self.filters["analysis_status"]])

    sb = MagicMock()
    sb.table.side_effect = Q
    nodes._status = None
    with patch("app.services.nodes.get_supabase", return_value=sb):
        s = nodes.NodeService().status()
    nodes._status = None
    assert s["queue"]["total"] == 1001 and s["etaHours"] == 5.0
    desk = s["machines"][0]
    assert desk["machine"] == "desk" and desk["engines"] == 1 and desk["searchedLastHour"] == 2 and desk["positionsToday"] == 80
    assert s["rates"] == {"allPerHour": 20, "nodesPerHour": 2, "serverPerHour": 18}


def test_the_node_modules_import_without_the_server_only_packages():
    """The node installs only requirements-node.txt: the shared modules must not need supabase, httpx, fastapi."""
    import subprocess
    import sys
    from pathlib import Path

    code = (
        "import sys, importlib.abc\n"
        "class B(importlib.abc.MetaPathFinder):\n"
        "    def find_spec(self, name, path, target=None):\n"
        "        if name.split('.')[0] in ('supabase', 'httpx', 'postgrest', 'fastapi', 'anthropic'): raise ImportError(name)\n"
        "sys.meta_path.insert(0, B())\n"
        "import app.services.move_classifier, app.services.position_evals, app.services.stockfish, app.services.threats\n"
    )
    api = Path(__file__).resolve().parents[1]
    result = subprocess.run([sys.executable, "-c", code], cwd=api, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr[-500:]
