"""'Chess.com called this Brilliant' (app/services/brilliant_reports.py, plan 3.3)."""

from pathlib import Path
from unittest.mock import patch

import chess

from app.services.brilliant_reports import BrilliantReportService, clause_title

MIGRATION = Path(__file__).resolve().parents[3] / "supabase" / "migrations" / "20261024003000_brilliant_reports.sql"
PGN = '[Event "?"]\n\n1. e4 e5 2. Qh5 Nf6 3. Qxf7+ *'


def test_failed_clause_is_the_first_the_rule_stops_at():
    # 2.Qh5 offers nothing: the first clause fails before soundness is even asked.
    game = {"pgn": PGN, "source": "chess_com", "time_control": "600", "user_rating": 700}
    row = {"ply": 2, "uci": "d1h5", "eval_before": 0.3, "eval_after": 0.1, "cp_loss": 20, "best_uci": "g1f3", "pv": []}
    with patch("app.services.brilliant_reports.get_supabase") as sb, patch("app.services.brilliant_reports.get_human_model_for_game"):
        sb.return_value.table.return_value.select.return_value.eq.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value.data = []
        assert BrilliantReportService().failed_clause(game, row) == "real_sacrifice"
    assert clause_title("sound") == "It holds up"


def test_migration_has_rls_and_no_free_text():
    sql = MIGRATION.read_text(encoding="utf-8")
    assert "enable row level security" in sql and "failed_clause in (" in sql
    assert "note" not in sql and "text not null check (source in" in sql


def test_route_reports_and_404s():
    from fastapi.testclient import TestClient

    from app.main import app

    client = TestClient(app)
    with patch("app.routers.games.require_game_access"), patch("app.services.brilliant_reports.BrilliantReportService.report", return_value={"clause": "sound", "line": "Thanks."}) as rep:
        res = client.post("/games/g1/moves/12/brilliant-report", json={"source": "chess_com"})
        assert res.status_code == 200 and res.json()["clause"] == "sound"
        assert rep.call_args.args[:3] == ("g1", 12, "chess_com")
    with patch("app.routers.games.require_game_access"), patch("app.services.brilliant_reports.BrilliantReportService.report", return_value=None):
        assert client.post("/games/g1/moves/12/brilliant-report", json={}).status_code == 404
    assert client.post("/games/g1/moves/12/brilliant-report", json={"source": "fide"}).status_code == 422
