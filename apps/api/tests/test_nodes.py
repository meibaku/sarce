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
    sb.table.return_value.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value.data = [{"id": "a"}, {"id": "b"}]
    service = AnalysisService()
    seen = []

    async def fake_analyze(game_id):
        seen.append(game_id)
        return {"gameId": game_id}

    with patch("app.services.analysis.get_supabase", return_value=sb), patch("app.services.nodes.live_leases", return_value={"a"}), patch.object(service, "analyze_game", side_effect=fake_analyze):
        asyncio.run(service.analyze_pending(limit=2))
    assert "a" not in seen
