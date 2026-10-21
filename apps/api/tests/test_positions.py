import pytest

from app.services.positions import clean_fen, drill_items

START = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"


def test_clean_fen_accepts_playable_positions_only():
    assert clean_fen(START) == START
    with pytest.raises(ValueError):
        clean_fen("8/8/8/8/8/8/8/8 w - - 0 1")  # no kings
    with pytest.raises(ValueError):
        clean_fen("rnb1kbnr/pppp1ppp/8/4p3/6Pq/5P2/PPPPP2P/RNBQKBNR w KQkq - 1 3")  # checkmated


def test_drill_items_carry_the_answer_when_known():
    items = drill_items([
        {"id": "a", "fen": START, "title": "vs bob, 12. Nf5", "note": "", "best_san": "Nf5", "game_id": "g", "ply": 22},
        {"id": "b", "fen": START, "title": "From a video", "note": "Kasparov's idea", "best_san": None, "game_id": None, "ply": None},
    ])
    assert items[0]["key"] == "saved:a" and items[0]["answer"] == "Nf5" and items[0]["source"] == "a saved position"
    assert items[1]["answer"] is None and items[1]["detail"] == "Kasparov's idea"
