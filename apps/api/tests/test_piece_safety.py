"""Golden LE2 piece-safety detector fixtures and fixed-search provenance."""

import json
from pathlib import Path
from unittest.mock import patch

import chess
import pytest

from app.services.piece_safety import candidate_after_move, classify_position

FIXTURES = json.loads((Path(__file__).parent / "fixtures" / "piece_safety_v1.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize("case", FIXTURES, ids=lambda case: case["name"])
def test_piece_safety_golden_cases(case):
    out = classify_position(chess.Board(case["fen"]), case["lines"], case["playerEpBefore"])
    assert out["eligible"] is True
    assert out["label"] == case["label"]
    assert out["relation"] == case["relation"]
    if case.get("square"):
        assert out["target"]["squares"] == [case["square"]]
    else:
        assert out["target"]["noImmediateDanger"] is True


def test_decided_and_missing_engine_positions_fail_closed():
    board = chess.Board(FIXTURES[0]["fen"])
    assert classify_position(board, FIXTURES[0]["lines"], 0.99) == {"eligible": False, "reason": "terminal_or_decided"}
    assert classify_position(board, [], 0.5) == {"eligible": False, "reason": "missing_engine_contract"}


def test_candidate_requires_the_fixed_search_and_records_provenance():
    board = chess.Board("4r1k1/8/8/8/8/8/8/4Q1K1 w - - 0 1")
    played = chess.Move.from_uci("e1e2")
    evaluation = {"nodes": 1_500_000, "engine_version": "Stockfish 18", "lines": [{"move_uci": "e8e2", "ep": 0.8}]}
    with patch("app.services.piece_safety.settings.analysis_nodes", 1_500_000):
        row = candidate_after_move(
            board_before=board,
            played=played,
            player_ep_before=0.5,
            evaluation=evaluation,
            owner_id="00000000-0000-4000-8000-000000000001",
            game_id="10000000-0000-4000-8000-000000000001",
            ply=12,
        )
        assert row and row["label"] == "positive"
        assert row["analysis_nodes"] == 1_500_000 and row["detector_version"] == 1
        assert row["verification"]["bestMoveUci"] == "e8e2"

        with pytest.raises(ValueError, match="fixed search"):
            candidate_after_move(
                board_before=board,
                played=played,
                player_ep_before=0.5,
                evaluation={**evaluation, "nodes": 200_000},
                owner_id="00000000-0000-4000-8000-000000000001",
                game_id="10000000-0000-4000-8000-000000000001",
                ply=12,
            )
