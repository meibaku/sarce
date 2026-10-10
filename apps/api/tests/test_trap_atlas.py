"""Rating-band trap atlas — Chaos Lens M6 (docs/CHAOS_PLAN.md). No engine or database."""

from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app
from app.services.trap_atlas import build_traps, to_api

client = TestClient(app)
MIGRATION = Path(__file__).resolve().parents[3] / "supabase" / "migrations" / "20261010004000_trap_atlas.sql"
FEN = "r1bqkbnr/pppp1ppp/2n5/4p2Q/2B1P3/8/PPPP1PPP/RNB1K1NR b KQkq - 3 3"


def obs(reply, loss, band=1200, key="k1", **extra):
    return {
        "fen_key": key, "fen": FEN, "band": band, "speed": "bullet", "reply_uci": reply,
        "reply_ep_loss": loss, "best_reply_uci": "g7g6", "p_fail": 0.6, "stake": 0.5, "eco": "C20",
        **extra,
    }


class TestBuildTraps:
    def test_common_losing_reply_is_a_trap(self):
        traps = build_traps([obs("g8f6", 0.9), obs("g8f6", 0.9), obs("g8f6", 0.9), obs("g7g6", 0.0)])
        assert len(traps) == 1
        trap = traps[0]
        assert trap["common_reply_uci"] == "g8f6"
        assert trap["frequency"] == 4
        assert trap["common_reply_share"] == 0.75
        assert trap["ep_loss"] == 0.9
        assert trap["best_reply_uci"] == "g7g6"
        assert (trap["p_fail"], trap["stake"], trap["eco"]) == (0.6, 0.5, "C20")

    def test_common_reply_that_holds_is_not_a_trap(self):
        assert build_traps([obs("g7g6", 0.0), obs("g7g6", 0.01), obs("g8f6", 0.9)]) == []

    def test_rare_positions_are_ignored(self):
        assert build_traps([obs("g8f6", 0.9), obs("g8f6", 0.9)]) == []

    def test_bands_are_separate(self):
        low = [obs("g8f6", 0.9, band=1000)] * 3
        high = [obs("g7g6", 0.0, band=2000)] * 3
        assert [t["band"] for t in build_traps(low + high)] == [1000]

    def test_worst_and_most_common_first(self):
        mild = [obs("a7a6", 0.25, key="k2")] * 3
        severe = [obs("g8f6", 0.9)] * 3
        assert [t["fen_key"] for t in build_traps(mild + severe)] == ["k1", "k2"]

    def test_blank_csv_values_do_not_break_the_means(self):
        traps = build_traps([obs("g8f6", 0.9, p_fail="", stake=None)] * 3)
        assert traps[0]["p_fail"] is None and traps[0]["stake"] is None


class TestApi:
    def test_to_api_shape(self):
        row = build_traps([obs("g8f6", 0.9)] * 3)[0]
        assert to_api(row) == {
            "fen": FEN, "band": 1200, "speed": "bullet", "frequency": 3,
            "commonReplyUci": "g8f6", "commonReplyShare": 1.0, "epLoss": 0.9,
            "bestReplyUci": "g7g6", "pFail": 0.6, "stake": 0.5, "eco": "C20",
        }

    @patch("app.routers.traps.trap_atlas_service.list_traps", return_value=[])
    def test_list_traps_passes_filters(self, mock_list):
        res = client.get("/traps?band=1200&eco=c2&limit=5")
        assert res.status_code == 200 and res.json() == {"traps": []}
        mock_list.assert_called_once_with(band=1200, eco="C2", limit=5)

    def test_rejects_a_malformed_eco_filter(self):
        assert client.get("/traps?eco=%25%25").status_code == 422

    def test_migration_enables_rls(self):
        sql = MIGRATION.read_text(encoding="utf-8")
        assert "alter table public.trap_atlas enable row level security" in sql
        assert "create policy" in sql
