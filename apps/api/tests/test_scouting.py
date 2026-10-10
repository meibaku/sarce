"""Opponent scouting — Chaos Lens M8. No network or database."""

from pathlib import Path
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.main import app
from app.services.scouting import build_scouting_report, to_api

client = TestClient(app)
MIGRATION = Path(__file__).resolve().parents[3] / "supabase" / "migrations" / "20261010006000_scouting_reports.sql"

KINGS_GAMBIT = '[ECO "C33"]\n[Opening "King\'s Gambit Accepted"]\n\n1. e4 e5 2. f4 exf4 3. Nf3 g5 4. Bc4 g4 5. O-O gxf3 6. Qxf3 *'
QUIET = '[ECO "C50"]\n[Opening "Italian Game"]\n\n1. e4 e5 2. Nf3 Nc6 3. Bc4 Bc5 *'


def parsed(pgn, color="white", result="win", time_control="60"):
    return {"pgn": pgn, "user_color": color, "result": result, "time_control": time_control}


class TestBuildReport:
    def test_aggregates_results_openings_and_time_controls(self):
        report = build_scouting_report(
            [parsed(KINGS_GAMBIT), parsed(KINGS_GAMBIT, result="loss"), parsed(QUIET, color="black", time_control="180")]
        )
        assert report["gamesSampled"] == 3
        assert report["results"] == {"win": 2, "loss": 1}
        assert report["openingsAsWhite"] == [{"name": "King's Gambit Accepted", "games": 2}]
        assert report["openingsAsBlack"] == [{"name": "Italian Game", "games": 1}]
        assert report["timeControls"][0] == {"name": "60", "games": 2}

    def test_motifs_count_only_the_scouted_players_moves(self):
        as_white = build_scouting_report([parsed(KINGS_GAMBIT)])
        as_black = build_scouting_report([parsed(KINGS_GAMBIT, color="black")])
        # White offers the f-pawn; Black's sacrifice in this line is a different move.
        assert as_white["motifsPer100Moves"]["sacrifice"] > 0
        assert as_white["motifsPer100Moves"] != as_black["motifsPer100Moves"]

    def test_gambit_tendency_is_reported_per_game(self):
        assert build_scouting_report([parsed(KINGS_GAMBIT)])["ideasPerGame"]["gambit"] == 1.0
        assert build_scouting_report([parsed(QUIET)])["ideasPerGame"]["gambit"] == 0.0

    def test_empty_and_unparseable_input(self):
        report = build_scouting_report([parsed(""), {"pgn": QUIET, "user_color": None}])
        assert report["gamesSampled"] == 0
        assert report["motifsPer100Moves"] == {} and report["ideasPerGame"] == {}

    def test_report_holds_no_pgn_or_game_links(self):
        text = str(build_scouting_report([parsed(KINGS_GAMBIT)]))
        assert "1. e4" not in text and "lichess.org" not in text and "chess.com" not in text


class TestRoutes:
    ROW = {
        "id": "r1", "target_username": "tal_fan", "source": "lichess",
        "games_sampled": 3, "created_at": "2026-10-10T00:00:00Z", "report": {"gamesSampled": 3},
    }

    @patch("app.routers.scouting.scouting_service.create_report", new_callable=AsyncMock)
    def test_create_report(self, mock_create):
        mock_create.return_value = to_api(self.ROW)
        res = client.post("/scouting/reports", json={"username": "Tal_Fan", "source": "lichess", "max_games": 20})
        assert res.status_code == 200 and res.json()["username"] == "tal_fan"
        kwargs = mock_create.await_args.kwargs
        assert (kwargs["username"], kwargs["source"], kwargs["max_games"]) == ("Tal_Fan", "lichess", 20)

    def test_rejects_unknown_site_and_odd_usernames(self):
        assert client.post("/scouting/reports", json={"username": "x", "source": "fide"}).status_code == 422
        assert client.post("/scouting/reports", json={"username": "a/../b"}).status_code == 422
        assert client.post("/scouting/reports", json={"username": "x", "max_games": 5000}).status_code == 422

    @patch("app.routers.scouting.scouting_service.list_reports", return_value=[])
    def test_list_is_scoped_to_the_caller(self, mock_list):
        assert client.get("/scouting/reports?user_id=u-1").json() == {"reports": []}
        mock_list.assert_called_once_with("u-1")

    @patch("app.routers.scouting.scouting_service.delete_report", return_value=False)
    def test_deleting_someone_elses_report_is_404(self, _mock):
        assert client.delete("/scouting/reports/r1").status_code == 404

    @patch("app.routers.scouting.scouting_service.delete_target", return_value=2)
    def test_deletion_on_request(self, mock_delete):
        assert client.delete("/scouting/targets/lichess/Tal_Fan").json() == {"deleted": 2}
        mock_delete.assert_called_once_with("lichess", "Tal_Fan", owner_user_id=None)


class TestMigration:
    def test_reports_are_owner_only(self):
        sql = MIGRATION.read_text(encoding="utf-8")
        assert "alter table public.scouting_reports enable row level security" in sql
        assert sql.count("owner_user_id = auth.uid()") == 2
        assert "to authenticated" not in sql and "using (true)" not in sql
