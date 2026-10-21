"""After-game Summary helpers and routes (app/services/summary.py)."""

from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app
from app.services import summary

client = TestClient(app)


class TestWording:
    def test_headline_matches_the_handoff(self):
        assert summary.headline(2, 1, 1) == "Two real problems set. One sacrifice held."
        assert summary.headline(0, 2, 0) == "Two sacrifices tried."
        assert summary.headline(0, 0, 0) == "A quiet game. No real problems set."

    def test_outcome_banner(self):
        won = summary.outcome("win", 34, "19. Rxe5", 3)
        assert won == {"kicker": "Brilliant !!", "accent": True, "text": "19. Rxe5 held. It goes on your timeline."}
        lost = summary.outcome("loss", 41, None, 2)
        assert lost["text"] == "Lost on move 41. Two moments are still worth a look."
        assert not lost["accent"]
        assert summary.outcome("draw", 52, None, 0)["text"] == "Drawn on move 52. Both sides kept the balance."


class TestNumbers:
    def test_style_read_is_bounded(self):
        assert summary.style_read(6.0, 6, 3, 0, 0) == 100
        assert summary.style_read(0.0, 6, 0, 0, 4) == 0
        assert summary.style_read(3.0, 6, 0, 0, 0) == 50

    def test_clock_and_lichess_link(self):
        assert summary.clock_label(31_400) == "0:31"
        assert summary.clock_label(None) is None
        assert summary.lichess_analysis_url(["e4", "e5", "Nf3"]) == "https://lichess.org/analysis/pgn/1.e4_e5_2.Nf3"


class TestRoutes:
    def test_summary_404_when_missing(self):
        with patch("app.routers.games.summary_service.summary", return_value=None):
            assert client.get("/games/nope/summary").status_code == 404

    def test_felt_validates_and_saves(self):
        with patch("app.routers.games.summary_service.set_felt") as save:
            assert client.post("/games/g1/felt", json={"answer": "maybe"}).status_code == 422
            res = client.post("/games/g1/felt", json={"answer": "partly"})
        assert res.status_code == 200 and res.json() == {"gameId": "g1", "felt": "partly"}
        save.assert_called_once_with("g1", "partly")


def test_move_label_uses_zero_based_plies():
    assert summary.move_label(36, "Rxe5") == "19. Rxe5"
    assert summary.move_label(45, "Qh4") == "23. …Qh4"
