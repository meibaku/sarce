"""Train helpers and routes (app/services/train.py)."""

from datetime import datetime, timezone
from unittest.mock import patch

import chess
from fastapi.testclient import TestClient

from app.main import app
from app.services import train

client = TestClient(app)


def test_band_for():
    assert train.band_for([1550, 1650]) == 1400 or train.band_for([1550, 1650]) == 1600
    assert train.band_for([]) == 1600
    assert train.band_for([300, 500]) == 800


def test_spacing():
    now = datetime(2026, 10, 18, tzinfo=timezone.utc)
    assert train.next_due("guessed", now).day == 19
    assert train.next_due("sure", now).day == 27


def test_missed_sacrifice_only_for_genuine_offers():
    board = chess.Board("6k1/5p2/4n3/8/8/8/8/4R1K1 w - - 0 1")
    played = chess.Move.from_uci("g1g2")
    assert train.missed_sacrifice(board, played, "e1e6") == chess.Move.from_uci("e1e6")
    assert train.missed_sacrifice(board, played, "g1h2") is None
    assert train.missed_sacrifice(board, played, None) is None


def test_answer_route_validates():
    with patch("app.routers.users.train_service.answer", side_effect=ValueError("bad")):
        assert client.post("/users/train/answer", json={"drillKey": "k", "confidence": "maybe"}).status_code == 422
    with patch("app.routers.users.train_service.answer", return_value={"inDays": 3}):
        assert client.post("/users/train/answer", json={"drillKey": "k", "confidence": "unsure"}).json() == {"inDays": 3}
