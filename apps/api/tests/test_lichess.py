"""Lichess import — Chaos Lens M8. No network."""

from pathlib import Path
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.main import app
from app.services.lichess import normalize_lichess_username, parse_lichess_game, parse_ndjson

client = TestClient(app)
MIGRATION = Path(__file__).resolve().parents[3] / "supabase" / "migrations" / "20261010005000_game_source.sql"


def raw_game(**overrides) -> dict:
    game = {
        "id": "abcd1234",
        "variant": "standard",
        "status": "mate",
        "lastMoveAt": 1_760_000_000_000,
        "players": {
            "white": {"user": {"name": "Tal_Fan"}, "rating": 1510},
            "black": {"user": {"name": "Opponent"}, "rating": 1480},
        },
        "winner": "white",
        "clock": {"initial": 60, "increment": 0},
        "pgn": '[Event "Rated bullet game"]\n\n1. e4 { [%clk 0:01:00] } e5 { [%clk 0:01:00] } 1-0',
    }
    return {**game, **overrides}


class TestParseLichessGame:
    def test_white_user_win(self):
        parsed = parse_lichess_game(raw_game(), "tal_fan")
        assert parsed == {
            "external_id": "https://lichess.org/abcd1234",
            "pgn": raw_game()["pgn"],
            "played_at": "2025-10-09T08:53:20+00:00",
            "opponent": "Opponent",
            "opponent_rating": 1480,
            "time_control": "60",
            "result": "win",
            "user_color": "white",
        }

    def test_black_user_sees_a_loss(self):
        parsed = parse_lichess_game(raw_game(), "OPPONENT")
        assert (parsed["user_color"], parsed["result"], parsed["opponent_rating"]) == ("black", "loss", 1510)

    def test_no_winner_is_a_draw(self):
        game = raw_game(status="draw")
        del game["winner"]
        assert parse_lichess_game(game, "tal_fan")["result"] == "draw"

    def test_increment_is_kept_in_the_time_control(self):
        assert parse_lichess_game(raw_game(clock={"initial": 180, "increment": 2}), "tal_fan")["time_control"] == "180+2"

    def test_unfinished_games_are_never_imported(self):
        assert parse_lichess_game(raw_game(status="started"), "tal_fan") is None
        assert parse_lichess_game(raw_game(status="created"), "tal_fan") is None

    def test_variants_and_strangers_games_are_skipped(self):
        assert parse_lichess_game(raw_game(variant="chess960"), "tal_fan") is None
        assert parse_lichess_game(raw_game(), "someone_else") is None
        assert parse_lichess_game(raw_game(pgn=""), "tal_fan") is None

    def test_anonymous_opponent(self):
        game = raw_game()
        game["players"]["black"] = {"aiLevel": 3}
        parsed = parse_lichess_game(game, "tal_fan")
        assert (parsed["opponent"], parsed["opponent_rating"]) == ("unknown", None)


class TestHelpers:
    def test_ndjson_skips_blank_and_malformed_lines(self):
        assert parse_ndjson('{"id": "a"}\n\nnot json\n{"id": "b"}\n') == [{"id": "a"}, {"id": "b"}]

    def test_username_is_lowercased(self):
        assert normalize_lichess_username("  DrNykterstein ") == "drnykterstein"


class TestRoute:
    @patch("app.routers.games.analysis_service.analyze_pending", new_callable=AsyncMock)
    @patch("app.routers.games.game_store.store_parsed_games", new_callable=AsyncMock)
    @patch("app.routers.games.lichess.fetch_games", new_callable=AsyncMock)
    def test_import_stores_only_finished_games(self, mock_fetch, mock_store, mock_analyze):
        mock_fetch.return_value = [raw_game(), raw_game(id="live0001", status="started")]
        mock_store.return_value = 1

        res = client.post("/games/import/lichess", json={"username": " Tal_Fan ", "max_games": 5})

        assert res.status_code == 200
        assert res.json()["username"] == "tal_fan" and res.json()["imported"] == 1
        mock_fetch.assert_awaited_once_with("tal_fan", max_games=5)
        stored = mock_store.await_args.kwargs
        assert stored["source"] == "lichess"
        assert [g["external_id"] for g in stored["parsed_games"]] == ["https://lichess.org/abcd1234"]
        assert mock_analyze.await_args.kwargs["chess_com_username"] == "tal_fan"

    @patch("app.routers.games.lichess.fetch_games", new_callable=AsyncMock, side_effect=RuntimeError("boom"))
    def test_upstream_failure_is_a_502(self, _mock):
        assert client.post("/games/import/lichess", json={"username": "tal_fan"}).status_code == 502

    def test_migration_adds_source_with_a_check(self):
        sql = MIGRATION.read_text(encoding="utf-8")
        assert "add column if not exists source" in sql and "'lichess'" in sql
